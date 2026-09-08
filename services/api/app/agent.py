from __future__ import annotations

from uuid import UUID

from aethon.agent_brain import AgentBrain, BrainDecision, Plan, PlanStep, StepKind
from aethon.agent_learning import AgentLearning
from aethon.agent_state import AgentState, AgentStateStore
from aethon.approval_lifecycle import ApprovalLifecycle, ApprovalLifecycleError, ApprovalRequest
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.experience_generalization import ExperienceEvidence, ExperienceGeneralizer
from aethon.experience_retrieval import ExperienceCandidate, ExperienceRetriever
from aethon.memory_repository import MemoryRepository
from aethon.model_router import ModelRouter
from aethon.schemas import Event, Task, TaskStatus, ToolRequest
from aethon.security import SafetyKernel
from aethon.strategy_selection import AdaptiveStrategySelector
from aethon.tools import ToolRegistry
from aethon.verification import BasicVerifier, Verifier
from aethon.web_runtime import WebAwareVerifier


class ApprovalRequired(Exception):
    """Internal control-flow signal used to pause execution without replanning."""


class AgentRuntime:
    """Bounded Agent Brain runtime with persistent checkpoints and recovery."""

    def __init__(self, verifier: Verifier | None = None, memory=None, tools: ToolRegistry | None = None,
                 safety: SafetyKernel | None = None, brain: AgentBrain | None = None,
                 state_store: AgentStateStore | None = None, learning: AgentLearning | None = None):
        self.models = ModelRouter()
        self.verifier = verifier or WebAwareVerifier(BasicVerifier())
        self.memory = memory or MemoryRepository()
        self.tools = tools or ToolRegistry()
        self.safety = safety or SafetyKernel()
        self.safety_gate = SafetyExecutionGate(self.safety)
        self.brain = brain or AgentBrain()
        self.state_store = state_store or AgentStateStore()
        self.learning = learning or AgentLearning()
        self.approvals = ApprovalLifecycle()
        self.experience_generalizer = ExperienceGeneralizer()
        self.experience_retriever = ExperienceRetriever()
        self.strategy_selector = AdaptiveStrategySelector()
        self.events: dict[UUID, list[Event]] = {}

    def run(self, task: Task) -> Task:
        namespace = "project" if task.project_id else "default"
        saved = self.state_store.load(task.task_id)
        plan: Plan
        observations: list[object]
        answer = None
        context = self.memory.search(task.goal, owner_id=task.owner_id, project_id=task.project_id, namespace=namespace, limit=5)
        experience_context = self._experience_context(task, namespace)

        if saved and saved.status in {"PAUSED", "RUNNING", "RECOVERING", "AWAITING_APPROVAL"} and saved.plan:
            plan = self._plan_from_state(saved.plan)
            observations = list(saved.observations)
            self._event(task, "agent.state_restored", {"revision": plan.revision, "last_verified_step": saved.last_verified_step, "completed_steps": list(plan.completed_steps)})
            for step in plan.steps:
                if step.status not in {"SUCCEEDED", "PENDING"}:
                    step.status = "PENDING"
            if saved.status == "AWAITING_APPROVAL":
                task.error = None
                if any(item.get("status") == "APPROVED" for item in saved.approvals):
                    self._transition(task, TaskStatus.EXECUTING)
        else:
            self._transition(task, TaskStatus.PLANNING)
            self._audit(task, "task_started", {"project_id": task.project_id, "owner_id": task.owner_id})
            self._event(task, "memory.context_retrieved", {"project_id": task.project_id, "owner_id": task.owner_id, "namespace": namespace, "count": len(context), "memory_ids": [item.memory_id for item in context], "experience_count": len(experience_context)})
            plan = self.brain.initial_plan(task.goal, {spec.name for spec in self.tools.list()})
            observations = []
            self._emit_plan(task, plan, "plan.created")
            self._checkpoint(task, plan, observations, "RUNNING")
            self._transition(task, TaskStatus.EXECUTING)

        for _ in range(self.brain.max_steps + self.brain.max_replans + 2):
            if self.state_store.cancel_requested(task.task_id):
                task.status = TaskStatus.CANCELLED
                task.error = None
                self._checkpoint(task, plan, observations, "CANCELLED", last_verified_step=self._last_verified(plan))
                self._event(task, "task.cancelled", {"last_verified_step": self._last_verified(plan), "revision": plan.revision})
                self._audit(task, "task_cancelled", {"last_verified_step": self._last_verified(plan), "revision": plan.revision})
                self.state_store.clear_controls(task.task_id)
                return task
            if self.state_store.pause_requested(task.task_id):
                task.status = TaskStatus.PAUSED
                task.error = None
                self._checkpoint(task, plan, observations, "PAUSED", last_verified_step=self._last_verified(plan))
                self._event(task, "task.paused", {"last_verified_step": self._last_verified(plan), "revision": plan.revision, "completed_steps": list(plan.completed_steps)})
                self._audit(task, "task_paused", {"last_verified_step": self._last_verified(plan), "revision": plan.revision})
                return task
            if task.status == TaskStatus.CANCELLED:
                self._checkpoint(task, plan, observations, "CANCELLED")
                self._event(task, "task.cancelled", {})
                self.state_store.clear_controls(task.task_id)
                return task

            decision = self.brain.next_decision(plan)
            self._event(task, "brain.decision", {"action": decision.action, "reason": decision.reason, "step_id": decision.step.step_id if decision.step else None, "revision": plan.revision})
            self._checkpoint(task, plan, observations, "RUNNING")
            if decision.action == "FINISH": break
            if decision.action == "BLOCK":
                task.status = TaskStatus.BLOCKED
                task.error = decision.reason
                self._checkpoint(task, plan, observations, "BLOCKED")
                self._event(task, "task.blocked", {"reason": decision.reason})
                self.state_store.clear_controls(task.task_id)
                return task
            if decision.action == "WAIT" or decision.step is None:
                task.status = TaskStatus.FAILED
                task.error = "plan dependencies could not be satisfied"
                self._checkpoint(task, plan, observations, "FAILED")
                self._event(task, "task.failed", {"reason": task.error})
                self.state_store.clear_controls(task.task_id)
                return task

            step = decision.step
            self._event(task, "plan.step.started", {"step_id": step.step_id, "kind": step.kind.value, "description": step.description, "attempt": step.attempts + 1})
            self._checkpoint(task, plan, observations, "RUNNING")
            try:
                if step.kind == StepKind.TOOL:
                    output = self._execute_tool(task, step.step_id, step.tool, step.arguments)
                    observations.append(output)
                    answer = output
                elif step.kind == StepKind.REASON:
                    prompt = self._reason_prompt(task.goal, context, observations, step.description, experience_context)
                    answer = self.models.generate(prompt)
                    observations.append(answer)
                elif step.kind == StepKind.VERIFY:
                    candidate = answer or (observations[-1] if observations else "")
                    self._transition(task, TaskStatus.VERIFYING)
                    verification = self.verifier.verify(task.goal, candidate)
                    self._event(task, "verification.completed", {"step_id": step.step_id, "ok": verification.ok, "reason": verification.reason, "evidence": verification.evidence})
                    self._audit(task, "verification", {"step_id": step.step_id, "ok": verification.ok, "reason": verification.reason, "evidence": verification.evidence})
                    if not verification.ok:
                        replanned = self._replan(task, plan, step, verification.reason, observations)
                        if replanned.action == "BLOCK":
                            task.status = TaskStatus.BLOCKED
                            task.error = replanned.reason
                            self._checkpoint(task, plan, observations, "BLOCKED")
                            self._event(task, "task.blocked", {"reason": task.error})
                            self._audit(task, "task_blocked", {"reason": task.error})
                            self.state_store.clear_controls(task.task_id)
                            return task
                        if replanned.action == "FAIL":
                            task.status = TaskStatus.FAILED
                            task.error = f"verification failed: {verification.reason}"
                            self._checkpoint(task, plan, observations, "FAILED")
                            self._audit(task, "task_failed", {"reason": task.error})
                            self.state_store.clear_controls(task.task_id)
                            return task
                        self._checkpoint(task, plan, observations, "RECOVERING")
                        self._transition(task, TaskStatus.EXECUTING)
                        continue

                self.brain.record_success(plan, step.step_id)
                self._event(task, "plan.step.completed", {"step_id": step.step_id, "attempts": step.attempts, "completed_steps": list(plan.completed_steps)})
                self._checkpoint(task, plan, observations, "RUNNING", last_verified_step=step.step_id if step.kind == StepKind.VERIFY else None)
                if task.status == TaskStatus.VERIFYING:
                    self._transition(task, TaskStatus.EXECUTING)
            except ApprovalRequired as exc:
                task.status = TaskStatus.AWAITING_APPROVAL
                task.error = str(exc)
                self._checkpoint(task, plan, observations, "AWAITING_APPROVAL", last_verified_step=self._last_verified(plan))
                self._event(task, "task.awaiting_approval", {"reason": str(exc), "step_id": step.step_id, "tool": step.tool, "revision": plan.revision})
                self._audit(task, "approval_required", {"step_id": step.step_id, "tool": step.tool, "revision": plan.revision})
                return task
            except Exception as exc:
                replanned = self._replan(task, plan, step, str(exc), observations)
                if replanned.action == "BLOCK":
                    task.status = TaskStatus.BLOCKED
                    task.error = replanned.reason
                    self._checkpoint(task, plan, observations, "BLOCKED")
                    self._event(task, "task.blocked", {"reason": task.error})
                    self._audit(task, "task_blocked", {"reason": task.error})
                    self.state_store.clear_controls(task.task_id)
                    return task
                if replanned.action == "FAIL":
                    task.status = TaskStatus.FAILED
                    task.error = str(exc)
                    self._checkpoint(task, plan, observations, "FAILED")
                    self._audit(task, "task_failed", {"reason": task.error})
                    self.state_store.clear_controls(task.task_id)
                    return task
                self._checkpoint(task, plan, observations, "RECOVERING")
                self._transition(task, TaskStatus.EXECUTING)

        decision = self.brain.next_decision(plan)
        if decision.action != "FINISH":
            task.status = TaskStatus.BLOCKED
            task.error = "execution budget exhausted"
            self._checkpoint(task, plan, observations, "BLOCKED")
            self._event(task, "task.blocked", {"reason": task.error, "revision": plan.revision})
            self.state_store.clear_controls(task.task_id)
            return task

        task.result = answer
        verified = self._last_verified(plan) is not None
        record = self.memory.put(f"task:{task.task_id}:result", answer or "", owner_id=task.owner_id, project_id=task.project_id, namespace=namespace, memory_type="episodic", source="verified_task_result", confidence=1.0)
        self._event(task, "memory.result_stored", {"project_id": task.project_id, "owner_id": task.owner_id, "namespace": record.namespace, "memory_id": record.memory_id})
        if verified:
            signals = self.learning.deduplicate(self.learning.from_outcome(goal=task.goal, result=answer or "", verified=True))
            for index, signal in enumerate(signals):
                learning_id = f"learning:{task.task_id}:{index}"
                learning_record = self.memory.put(learning_id, signal.value, owner_id=task.owner_id, project_id=task.project_id, namespace=namespace, memory_type="semantic", source="agent_learning", confidence=signal.confidence)
                self._event(task, "memory.learning_stored", {"project_id": task.project_id, "owner_id": task.owner_id, "namespace": learning_record.namespace, "memory_id": learning_record.memory_id, "kind": signal.kind, "confidence": signal.confidence})
            self._audit(task, "learning_extracted", {"verified": True, "signals": len(signals)})
        else:
            self._audit(task, "learning_skipped", {"verified": False, "reason": "no successful verification step"})
        self._transition(task, TaskStatus.SUCCEEDED)
        self._checkpoint(task, plan, observations, "SUCCEEDED", last_verified_step=self._last_verified(plan))
        self._audit(task, "task_succeeded", {"verified": verified, "plan_revision": plan.revision, "completed_steps": list(plan.completed_steps)})
        self.state_store.clear_controls(task.task_id)
        return task

    def approve(self, task_id: UUID | str, step_id: str, approver: str) -> Task:
        """Record explicit approval for a paused task; execution resumes via run()."""
        task_key = str(task_id)
        saved = self.state_store.load(task_key)
        if saved is None or saved.status != "AWAITING_APPROVAL":
            raise ApprovalLifecycleError("task is not awaiting approval")
        pending = next((item for item in saved.approvals if item.get("task_id") == task_key and item.get("step_id") == step_id and item.get("status") == "PENDING"), None)
        if pending is None:
            raise ApprovalLifecycleError("no pending approval for task step")
        if not self.approvals.pending(task_key, step_id):
            self.approvals.request(ApprovalRequest(task_key, step_id, pending["tool"], pending["risk"], bool(pending["side_effects"])))
        approved = self.approvals.approve(task_key, step_id, approver)
        for item in saved.approvals:
            if item.get("task_id") == task_key and item.get("step_id") == step_id and item.get("status") == "PENDING":
                item.update({"status": "APPROVED", "approver": approved.approver})
        self.state_store.save(AgentState(task_id=saved.task_id, plan=saved.plan, observations=saved.observations, approvals=saved.approvals, recovery_history=saved.recovery_history, last_verified_step=saved.last_verified_step, status="AWAITING_APPROVAL"))
        event_task = Task(task_id=UUID(task_key), goal=saved.plan.get("goal", ""), status=TaskStatus.AWAITING_APPROVAL)
        self._event(event_task, "approval.granted", {"step_id": step_id, "tool": approved.tool, "approver": approved.approver})
        self._audit(event_task, "approval_granted", {"step_id": step_id, "tool": approved.tool, "approver": approved.approver})
        return event_task

    def _experience_context(self, task: Task, namespace: str) -> tuple[str, ...]:
        memories = self.memory.search(task.goal, owner_id=task.owner_id, project_id=task.project_id, namespace=namespace, limit=20)
        evidence = tuple(ExperienceEvidence(item.memory_id, item.content, item.confidence, item.source) for item in memories if item.source == "agent_learning")
        patterns = self.experience_generalizer.generalize(evidence)
        candidates = tuple(ExperienceCandidate("experience:" + ":".join(pattern.evidence_ids), pattern.pattern, pattern.confidence) for pattern in patterns)
        ranked = self.experience_retriever.rank(task.goal, candidates)
        selection = self.strategy_selector.select(task.goal, ranked)
        if selection.selected:
            self._event(task, "strategy.selected", {"experience_id": selection.selected.experience_id, "score": selection.selected.score, "confidence": selection.selected.confidence, "reason": selection.selected.reason})
        return self.experience_retriever.build_context(task.goal, candidates) + ((selection.context,) if selection.selected else ())

    def _replan(self, task, plan: Plan, step, reason: str, observations: list[object]) -> BrainDecision:
        decision = self.brain.replan(plan, step.step_id, reason, available_tools={spec.name for spec in self.tools.list()}, observations=observations)
        self._emit_replan(task, plan, decision)
        self._checkpoint(task, plan, observations, "RECOVERING")
        return decision

    def _execute_tool(self, task: Task, step_id: str, tool_name: str | None, arguments: dict) -> object:
        if not tool_name: raise ValueError("tool step missing tool name")
        spec = next((item for item in self.tools.list() if item.name == tool_name), None)
        if not spec: raise ValueError(f"tool not found: {tool_name}")
        approved = self._has_persisted_approval(task, step_id, tool_name)
        try:
            authorization = self.safety_gate.authorize(spec.risk, spec.side_effects, approved=approved)
        except ExecutionAuthorizationError as exc:
            if self.safety.authorize(spec.risk, spec.side_effects) == "APPROVAL_REQUIRED" and not approved:
                self._request_approval(task, step_id, spec)
                raise ApprovalRequired(f"approval required for tool: {tool_name}") from exc
            raise PermissionError(str(exc)) from exc
        self._event(task, "tool.authorization", {"tool": tool_name, "decision": authorization.effective_decision, "policy_decision": authorization.policy_decision, "risk": spec.risk.value, "side_effects": spec.side_effects, "step_id": step_id, "approved": approved})
        if approved:
            self._consume_persisted_approval(task, step_id, tool_name)
        result = self.tools.execute(ToolRequest(tool=tool_name, arguments=arguments))
        self._event(task, "tool.observed", {"tool": tool_name, "ok": result.ok, "output_type": type(result.output).__name__ if result.ok else None, "error": result.error if not result.ok else None})
        if not result.ok: raise RuntimeError(result.error or f"tool failed: {tool_name}")
        return result.output

    def _request_approval(self, task: Task, step_id: str, spec) -> None:
        request = ApprovalRequest(str(task.task_id), step_id, spec.name, spec.risk.value, spec.side_effects)
        self.approvals.request(request)
        saved = self.state_store.load(task.task_id)
        approvals = list(saved.approvals) if saved else []
        approvals = [item for item in approvals if not (item.get("task_id") == request.task_id and item.get("step_id") == request.step_id)]
        approvals.append({"task_id": request.task_id, "step_id": request.step_id, "tool": request.tool, "risk": request.risk, "side_effects": request.side_effects, "status": "PENDING"})
        if saved:
            self.state_store.save(AgentState(task_id=saved.task_id, plan=saved.plan, observations=saved.observations, approvals=approvals, recovery_history=saved.recovery_history, last_verified_step=saved.last_verified_step, status=saved.status))

    def _has_persisted_approval(self, task: Task, step_id: str, tool_name: str) -> bool:
        saved = self.state_store.load(task.task_id)
        return bool(saved and any(item.get("task_id") == str(task.task_id) and item.get("step_id") == step_id and item.get("tool") == tool_name and item.get("status") == "APPROVED" for item in saved.approvals))

    def _consume_persisted_approval(self, task: Task, step_id: str, tool_name: str) -> None:
        saved = self.state_store.load(task.task_id)
        if not saved:
            raise ApprovalLifecycleError("task state missing while consuming approval")
        matching = next((item for item in saved.approvals if item.get("task_id") == str(task.task_id) and item.get("step_id") == step_id and item.get("tool") == tool_name and item.get("status") == "APPROVED"), None)
        if matching is None:
            raise ApprovalLifecycleError("approval missing or mismatched")
        if not self.approvals.pending(str(task.task_id), step_id):
            self.approvals.request(ApprovalRequest(str(task.task_id), step_id, matching["tool"], matching["risk"], bool(matching["side_effects"])))
        self.approvals.consume(str(task.task_id), step_id, tool_name)
        approvals = [item for item in saved.approvals if item is not matching]
        self.state_store.save(AgentState(task_id=saved.task_id, plan=saved.plan, observations=saved.observations, approvals=approvals, recovery_history=saved.recovery_history, last_verified_step=saved.last_verified_step, status=saved.status))
        self._event(task, "approval.consumed", {"step_id": step_id, "tool": tool_name})

    def _checkpoint(self, task: Task, plan: Plan, observations: list[object], status: str, last_verified_step: str | None = None) -> None:
        self.state_store.save(AgentState(task_id=task.task_id, plan=self._plan_to_state(plan, task.goal), observations=observations, approvals=self._current_approvals(task), recovery_history=[], last_verified_step=last_verified_step, status=status))

    def _current_approvals(self, task: Task) -> list[dict]:
        saved = self.state_store.load(task.task_id)
        return list(saved.approvals) if saved else []

    def _plan_to_state(self, plan: Plan, goal: str) -> dict:
        return {"goal": goal, "revision": plan.revision, "steps": [{"step_id": step.step_id, "kind": step.kind.value, "description": step.description, "tool": step.tool, "arguments": step.arguments, "status": step.status, "attempts": step.attempts} for step in plan.steps], "completed_steps": list(plan.completed_steps)}

    def _plan_from_state(self, payload: dict) -> Plan:
        return Plan(revision=int(payload["revision"]), steps=[PlanStep(step_id=item["step_id"], kind=StepKind(item["kind"]), description=item["description"], tool=item.get("tool"), arguments=item.get("arguments", {}), status=item.get("status", "PENDING"), attempts=int(item.get("attempts", 0))) for item in payload["steps"]], completed_steps=list(payload.get("completed_steps", [])))

    def _last_verified(self, plan: Plan) -> str | None:
        return next((step.step_id for step in reversed(plan.steps) if step.kind == StepKind.VERIFY and step.status == "SUCCEEDED"), None)

    def _reason_prompt(self, goal, context, observations, step_description, experience_context):
        return f"Goal: {goal}\nContext: {context}\nObservations: {observations}\nTask: {step_description}\nExperience: {experience_context}"

    def _emit_plan(self, task: Task, plan: Plan, event_type: str) -> None:
        self._event(task, event_type, self._plan_to_state(plan, task.goal))

    def _emit_replan(self, task: Task, plan: Plan, decision: BrainDecision) -> None:
        self._event(task, "plan.replanned", {"revision": plan.revision, "action": decision.action, "reason": decision.reason, "step_id": decision.step.step_id if decision.step else None})

    def _transition(self, task: Task, status: TaskStatus) -> None:
        task.status = status
        self._event(task, "task.state_changed", {"status": status.value})

    def _event(self, task: Task, event_type: str, data: dict) -> None:
        self.events.setdefault(task.task_id, []).append(Event(type=event_type, task_id=task.task_id, data=data))

    def _audit(self, task: Task, action: str, data: dict) -> None:
        self._event(task, f"audit.{action}", data)

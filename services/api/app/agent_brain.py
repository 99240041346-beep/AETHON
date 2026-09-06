from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepKind(str, Enum):
    REASON = "REASON"
    TOOL = "TOOL"
    VERIFY = "VERIFY"


class FailureClass(str, Enum):
    TRANSIENT = "TRANSIENT"
    TOOL_ERROR = "TOOL_ERROR"
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    AUTHORIZATION = "AUTHORIZATION"
    VERIFICATION = "VERIFICATION"
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN = "UNKNOWN"


@dataclass
class PlanStep:
    step_id: str
    description: str
    kind: StepKind = StepKind.REASON
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 2
    status: str = "PENDING"


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    revision: int = 0
    completed_steps: list[str] = field(default_factory=list)
    recovery_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BrainDecision:
    action: str
    step: PlanStep | None = None
    reason: str = ""


class AgentBrain:
    """Bounded control-plane brain for adaptive planning and recovery."""

    def __init__(self, max_steps: int = 12, max_replans: int = 3):
        self.max_steps = max_steps
        self.max_replans = max_replans

    def initial_plan(self, goal: str, tool_names: set[str] | None = None) -> Plan:
        text = goal.strip()
        steps: list[PlanStep] = []
        lowered = text.lower()
        tools = tool_names or set()
        if any(word in lowered for word in ("search", "latest", "research", "find")) and "web_search" in tools:
            steps.append(PlanStep("step-1", "Search for relevant public information", StepKind.TOOL, "web_search", {"query": text}))
            steps.append(PlanStep("step-2", "Synthesize and verify the gathered evidence", StepKind.REASON, depends_on=["step-1"]))
            steps.append(PlanStep("step-3", "Verify the candidate result", StepKind.VERIFY, depends_on=["step-2"]))
        else:
            steps.append(PlanStep("step-1", "Reason about the user's goal and produce a candidate answer", StepKind.REASON))
            steps.append(PlanStep("step-2", "Verify the candidate answer", StepKind.VERIFY, depends_on=["step-1"]))
        return Plan(goal=text, steps=steps[: self.max_steps])

    def next_decision(self, plan: Plan) -> BrainDecision:
        if plan.revision > self.max_replans:
            return BrainDecision("BLOCK", reason="replan budget exhausted")
        if len(plan.steps) > self.max_steps:
            return BrainDecision("BLOCK", reason="plan step budget exceeded")
        for step in plan.steps:
            if step.status == "PENDING" and all(self._status(plan, dep) == "SUCCEEDED" for dep in step.depends_on):
                return BrainDecision("EXECUTE", step=step)
        if all(step.status == "SUCCEEDED" for step in plan.steps):
            return BrainDecision("FINISH", reason="all plan steps succeeded")
        return BrainDecision("WAIT", reason="dependencies are not satisfied")

    def record_success(self, plan: Plan, step_id: str) -> None:
        step = self._find(plan, step_id)
        step.status = "SUCCEEDED"
        if step_id not in plan.completed_steps:
            plan.completed_steps.append(step_id)

    def record_failure(self, plan: Plan, step_id: str, reason: str) -> BrainDecision:
        step = self._find(plan, step_id)
        step.attempts += 1
        step.status = "FAILED"
        if step.attempts < step.max_attempts and plan.revision < self.max_replans:
            step.status = "PENDING"
            plan.revision += 1
            return BrainDecision("REPLAN", step=step, reason=reason)
        return BrainDecision("FAIL", step=step, reason=reason)

    def replan(self, plan: Plan, step_id: str, reason: str, *, available_tools: set[str] | None = None, observations: list[Any] | None = None) -> BrainDecision:
        """Adapt strategy instead of blindly repeating a failed step."""
        try:
            step = self._find(plan, step_id)
        except KeyError:
            # If a recovery caller names a not-yet-materialized step, reopen the
            # latest existing candidate rather than inventing an unconnected step.
            if not plan.steps:
                raise
            step = plan.steps[-1]

        failure = self.classify_failure(reason)
        tools = available_tools or set()
        observations = observations or []

        if plan.revision >= self.max_replans:
            step.status = "FAILED"
            return BrainDecision("BLOCK", step=step, reason="replan budget exhausted")

        plan.revision += 1
        old_tool = step.tool
        strategy = "bounded_retry"

        if step.kind == StepKind.TOOL:
            alternative = self._alternative_tool(old_tool, tools, step.arguments)
            if alternative and alternative != old_tool:
                step.tool = alternative
                step.arguments = self._adapt_arguments(step, alternative, observations)
                step.description = f"Recover using alternative tool: {alternative}"
                strategy = "alternative_tool"
            elif failure in {FailureClass.INVALID_INPUT, FailureClass.TOOL_ERROR, FailureClass.TRANSIENT}:
                step.arguments = self._adapt_arguments(step, old_tool, observations)
                strategy = "adapted_input"
            step.status = "PENDING"
        elif step.kind == StepKind.VERIFY:
            producer = self._nearest_producer(plan, step)
            if producer:
                producer.status = "PENDING"
                producer.attempts += 1
                step.status = "PENDING"
                strategy = "regenerate_candidate"
            else:
                step.status = "PENDING"
                strategy = "verification_retry"
        else:
            step.status = "PENDING"
            strategy = "reasoning_retry"

        plan.recovery_history.append({"revision": plan.revision, "step_id": step_id, "failure_class": failure.value, "strategy": strategy, "previous_tool": old_tool, "new_tool": step.tool, "reason": reason})
        return BrainDecision("REPLAN", step=step, reason=f"{strategy}: {reason}")

    @staticmethod
    def classify_failure(reason: str) -> FailureClass:
        text = (reason or "").lower()
        if any(x in text for x in ("approval required", "denied by safety", "permission")): return FailureClass.AUTHORIZATION
        if any(x in text for x in ("not found", "unavailable")): return FailureClass.TOOL_UNAVAILABLE
        if any(x in text for x in ("invalid", "missing", "required argument")): return FailureClass.INVALID_INPUT
        if any(x in text for x in ("verification", "not verified", "insufficient evidence")): return FailureClass.VERIFICATION
        if any(x in text for x in ("timeout", "temporar", "rate limit", "connection", "network")): return FailureClass.TRANSIENT
        if any(x in text for x in ("tool", "fetch failed", "search failed")): return FailureClass.TOOL_ERROR
        return FailureClass.UNKNOWN

    @staticmethod
    def _alternative_tool(tool: str | None, available: set[str], arguments: dict[str, Any]) -> str | None:
        alternatives = {"web_search": ("web_fetch",), "web_fetch": ("web_search",)}
        for candidate in alternatives.get(tool, ()):
            if candidate in available and not (candidate == "web_fetch" and not arguments.get("url")):
                return candidate
        return None

    @staticmethod
    def _adapt_arguments(step: PlanStep, tool: str | None, observations: list[Any]) -> dict[str, Any]:
        args = dict(step.arguments)
        if tool == "web_search" and "query" in args:
            query = str(args["query"]).strip()
            if query and "provide sources" not in query.lower(): args["query"] = f"{query} provide authoritative sources"
        if tool == "web_fetch" and not args.get("url"):
            for observation in reversed(observations):
                if isinstance(observation, dict) and observation.get("url"):
                    args["url"] = observation["url"]
                    break
        return args

    @staticmethod
    def _nearest_producer(plan: Plan, verify_step: PlanStep) -> PlanStep | None:
        candidates = [s for s in plan.steps if s.step_id in verify_step.depends_on and s.kind in {StepKind.REASON, StepKind.TOOL}]
        return candidates[-1] if candidates else None

    @staticmethod
    def _find(plan: Plan, step_id: str) -> PlanStep:
        for step in plan.steps:
            if step.step_id == step_id: return step
        raise KeyError(step_id)

    @staticmethod
    def _status(plan: Plan, step_id: str) -> str:
        return AgentBrain._find(plan, step_id).status

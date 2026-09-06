from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepKind(str, Enum):
    REASON = "REASON"
    TOOL = "TOOL"
    VERIFY = "VERIFY"


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


@dataclass
class BrainDecision:
    action: str
    step: PlanStep | None = None
    reason: str = ""


class AgentBrain:
    """Deterministic control-plane brain for bounded planning and replanning.

    Model reasoning can later supply plans, but this layer owns execution state,
    dependency checks, retry bounds and replan decisions.
    """

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
        else:
            steps.append(PlanStep("step-1", "Reason about the user's goal and produce a candidate answer", StepKind.REASON))
            steps.append(PlanStep("step-2", "Verify the candidate answer", StepKind.VERIFY, depends_on=["step-1"]))
        if len(steps) > self.max_steps:
            steps = steps[: self.max_steps]
        return Plan(goal=text, steps=steps)

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

    def record_failure(self, plan: Plan, step_id: str, reason: str) -> BrainDecision:
        step = self._find(plan, step_id)
        step.attempts += 1
        step.status = "FAILED"
        if step.attempts < step.max_attempts and plan.revision < self.max_replans:
            step.status = "PENDING"
            plan.revision += 1
            return BrainDecision("REPLAN", step=step, reason=reason)
        return BrainDecision("FAIL", step=step, reason=reason)

    @staticmethod
    def _find(plan: Plan, step_id: str) -> PlanStep:
        for step in plan.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(step_id)

    @staticmethod
    def _status(plan: Plan, step_id: str) -> str:
        return AgentBrain._find(plan, step_id).status

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import re
from typing import Any, Iterable


class PlanStepKind(str, Enum):
    ANALYZE = "ANALYZE"
    SEARCH = "SEARCH"
    FETCH = "FETCH"
    CALCULATE = "CALCULATE"
    SYNTHESIZE = "SYNTHESIZE"
    VERIFY = "VERIFY"


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    kind: PlanStepKind
    objective: str
    tool: str | None = None
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionPlan:
    goal: str
    steps: tuple[PlanStep, ...]
    max_steps: int
    strategy: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "max_steps": self.max_steps,
            "strategy": self.strategy,
            "steps": [asdict(step) | {"kind": step.kind.value} for step in self.steps],
        }


class AgentBrain:
    """Deterministic planning layer that bounds and explains agent execution.

    The brain proposes a plan; it never grants permission for side effects.
    Authorization remains the responsibility of the SafetyKernel/tool layer.
    """

    def __init__(self, max_steps: int = 8):
        if not 1 <= max_steps <= 32:
            raise ValueError("max_steps must be between 1 and 32")
        self.max_steps = max_steps

    def plan(self, goal: str, available_tools: Iterable[str] = ()) -> ExecutionPlan:
        text = " ".join(goal.strip().split())
        if not text:
            raise ValueError("goal cannot be empty")
        tools = {tool.lower() for tool in available_tools}
        steps: list[PlanStep] = []

        def add(kind: PlanStepKind, objective: str, tool: str | None = None) -> None:
            if len(steps) >= self.max_steps - 1:
                return
            step_id = f"s{len(steps) + 1}"
            deps = (steps[-1].step_id,) if steps else ()
            steps.append(PlanStep(step_id, kind, objective, tool, deps))

        add(PlanStepKind.ANALYZE, "Understand the goal, constraints, required output, and success criteria.")

        wants_web = bool(re.search(r"\b(search|latest|recent|news|look up|research|website|online|web)\b", text, re.I))
        wants_math = bool(re.search(r"\b(calculate|compute|sum|average|percentage|percent|equation|math)\b", text, re.I))

        if wants_web and "web_search" in tools:
            add(PlanStepKind.SEARCH, "Gather relevant public web evidence before synthesis.", "web_search")
            if "web_fetch" in tools:
                add(PlanStepKind.FETCH, "Fetch the strongest relevant sources for verification.", "web_fetch")
        elif wants_math and "calculator" in tools:
            add(PlanStepKind.CALCULATE, "Perform the required calculation with a deterministic tool.", "calculator")
        else:
            add(PlanStepKind.ANALYZE, "Work through the problem using the model's available reasoning context.")

        add(PlanStepKind.SYNTHESIZE, "Produce the requested result while respecting constraints and tool evidence.")
        add(PlanStepKind.VERIFY, "Check that the result addresses the goal and does not claim unverified actions.")

        return ExecutionPlan(
            goal=text,
            steps=tuple(steps[: self.max_steps]),
            max_steps=self.max_steps,
            strategy="bounded-plan-with-verification",
        )

    def replan(self, plan: ExecutionPlan, failure_reason: str) -> ExecutionPlan:
        reason = " ".join(failure_reason.strip().split()) or "previous step failed"
        if len(plan.steps) >= plan.max_steps:
            return plan
        next_id = f"s{len(plan.steps) + 1}"
        deps = (plan.steps[-1].step_id,) if plan.steps else ()
        step = PlanStep(next_id, PlanStepKind.ANALYZE, f"Reassess after failure: {reason}", None, deps)
        return ExecutionPlan(plan.goal, plan.steps + (step,), plan.max_steps, "bounded-replan-with-verification")

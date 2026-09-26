from __future__ import annotations

"""Bounded autonomous execution layer for ASTRA.

This layer composes the existing Planner, Executor, Verifier and RecoveryManager.
It does not introduce a second tool/runtime system.
"""

from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Callable

from .astra_core import AgentDefinition, AgentRun, Permission, Plan, PlanStep, RecoveryManager, RunStatus, ToolRegistry


@dataclass(frozen=True)
class Checkpoint:
    run_id: str
    completed_steps: tuple[str, ...]
    outputs: dict[str, Any]
    status: str


@dataclass
class AutonomousResult:
    run: AgentRun
    plan: Plan
    checkpoints: list[Checkpoint] = field(default_factory=list)


class AutonomousAgentEngine:
    """Execute dependency-aware plans with bounded retries and checkpoints."""

    def __init__(
        self,
        *,
        tools: ToolRegistry | None = None,
        checkpoint_sink: Callable[[Checkpoint], None] | None = None,
    ) -> None:
        from .astra_core import Executor, Planner, Verifier
        self.tools = tools or ToolRegistry()
        self.planner = Planner()
        self.executor = Executor(self.tools)
        self.verifier = Verifier()
        self.recovery = RecoveryManager()
        self.checkpoint_sink = checkpoint_sink

    def execute(
        self,
        *,
        run: AgentRun,
        definition: AgentDefinition,
        plan: Plan,
        arguments: dict[str, dict[str, Any]] | None = None,
        granted: set[Permission] | None = None,
        confirmed_steps: set[str] | None = None,
        expected: dict[str, Any] | None = None,
        resume: Checkpoint | None = None,
    ) -> AutonomousResult:
        if run.status is RunStatus.QUEUED:
            run.start()
        if run.status is not RunStatus.RUNNING:
            raise ValueError("autonomous execution requires a queued or running run")

        arguments = arguments or {}
        granted = granted or set()
        confirmed_steps = confirmed_steps or set()
        expected = expected or {}
        checkpoints: list[Checkpoint] = []

        completed = set(resume.completed_steps if resume else ())
        if resume:
            plan.outputs.update(resume.outputs)

        while len(completed) < len(plan.steps):
            step = plan.next_ready(completed)
            if step is None:
                missing = [s.id for s in plan.steps if s.id not in completed]
                raise RuntimeError(f"plan is blocked by unresolved dependencies: {missing}")

            attempt = 0
            while True:
                try:
                    run.check_limits(definition)
                    result = self.executor.execute_step(
                        run, definition, step, arguments.get(step.id, {}),
                        granted=granted, confirmed=step.id in confirmed_steps,
                    )
                    if step.id in expected and not self.verifier.verify(expected[step.id], result):
                        raise RuntimeError(f"verification failed for step {step.id}")
                    plan.outputs[step.id] = result
                    completed.add(step.id)
                    checkpoint = Checkpoint(
                        run.id, tuple(s.id for s in plan.steps if s.id in completed),
                        dict(plan.outputs), RunStatus.RUNNING.value,
                    )
                    checkpoints.append(checkpoint)
                    if self.checkpoint_sink:
                        self.checkpoint_sink(checkpoint)
                    break
                except Exception as exc:
                    if self.recovery.should_retry(exc, attempt, definition.max_retries):
                        attempt += 1
                        run.retries += 1
                        continue
                    if isinstance(exc, PermissionError) and step.id not in confirmed_steps:
                        run.status = RunStatus.WAITING_CONFIRMATION
                        checkpoint = Checkpoint(
                            run.id, tuple(s.id for s in plan.steps if s.id in completed),
                            dict(plan.outputs), run.status.value,
                        )
                        checkpoints.append(checkpoint)
                        if self.checkpoint_sink:
                            self.checkpoint_sink(checkpoint)
                        return AutonomousResult(run, plan, checkpoints)
                    run.fail(str(exc))
                    return AutonomousResult(run, plan, checkpoints)

        run.finish(plan.outputs)
        final = Checkpoint(
            run.id, tuple(s.id for s in plan.steps),
            dict(plan.outputs), run.status.value,
        )
        checkpoints.append(final)
        if self.checkpoint_sink:
            self.checkpoint_sink(final)
        return AutonomousResult(run, plan, checkpoints)

    def build(
        self,
        *,
        goal: str,
        steps: list[PlanStep],
        agent_id: str,
        run_id: str,
    ) -> tuple[AgentRun, Plan]:
        plan = self.planner.create(goal, steps)
        return AgentRun(run_id, agent_id, goal), plan

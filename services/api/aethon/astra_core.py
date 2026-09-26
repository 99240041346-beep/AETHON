from __future__ import annotations

"""Reusable ASTRA orchestration primitives.

These primitives are intentionally provider- and framework-neutral. They describe
execution state and enforce bounded planning/permission decisions without
pretending that an external action has happened.
"""

from dataclasses import dataclass, field
from enum import Enum
from time import monotonic
from typing import Any, Callable


class Permission(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    EXECUTE = "EXECUTE"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    ADMIN = "ADMIN"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    permission: Permission
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    risk: str = "low"
    timeout_seconds: float = 30.0
    max_retries: int = 0
    authentication_required: bool = False


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    depends_on: tuple[str, ...] = ()
    tool: str | None = None


@dataclass
class Plan:
    goal: str
    steps: list[PlanStep]
    current_step: int = 0
    retries: int = 0
    outputs: dict[str, Any] = field(default_factory=dict)

    def next_ready(self, completed: set[str]) -> PlanStep | None:
        for step in self.steps:
            if step.id in self.outputs:
                continue
            if all(dep in completed for dep in step.depends_on):
                return step
        return None


@dataclass
class AgentDefinition:
    id: str
    name: str
    description: str
    instructions: str = ""
    tools: tuple[str, ...] = ()
    permissions: tuple[Permission, ...] = (Permission.READ,)
    model: str | None = None
    max_steps: int = 20
    max_runtime_seconds: float = 300.0
    max_tool_calls: int = 30
    max_retries: int = 2


@dataclass
class AgentRun:
    id: str
    agent_id: str
    goal: str
    status: RunStatus = RunStatus.QUEUED
    steps: int = 0
    tool_calls: int = 0
    retries: int = 0
    started_at: float | None = None
    error: str | None = None
    outputs: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        if self.status is not RunStatus.QUEUED:
            raise ValueError("agent run can only start from queued state")
        self.status = RunStatus.RUNNING
        self.started_at = monotonic()

    def check_limits(self, definition: AgentDefinition) -> None:
        if self.steps >= definition.max_steps:
            raise RuntimeError("agent step limit exceeded")
        if self.tool_calls >= definition.max_tool_calls:
            raise RuntimeError("agent tool-call limit exceeded")
        if self.started_at is not None and monotonic() - self.started_at > definition.max_runtime_seconds:
            raise TimeoutError("agent runtime limit exceeded")

    def finish(self, outputs: dict[str, Any] | None = None) -> None:
        self.status = RunStatus.COMPLETED
        if outputs:
            self.outputs.update(outputs)

    def fail(self, error: str) -> None:
        self.status = RunStatus.FAILED
        self.error = error


class PermissionManager:
    def authorize(
        self,
        tool: ToolSpec,
        granted: set[Permission],
        *,
        confirmed: bool = False,
    ) -> bool:
        if tool.permission not in granted:
            return False
        if tool.permission is Permission.EXTERNAL_ACTION and not confirmed:
            return False
        if tool.permission is Permission.ADMIN and Permission.ADMIN not in granted:
            return False
        return True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, Callable[..., Any]]] = {}

    def register(self, spec: ToolSpec, execute: Callable[..., Any]) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, execute)

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name][0]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        granted: set[Permission],
        confirmed: bool = False,
    ) -> Any:
        spec, function = self._tools.get(name, (None, None))
        if spec is None:
            raise KeyError(f"unknown tool: {name}")
        if not isinstance(arguments, dict):
            raise TypeError("tool arguments must be an object")
        allowed = set(spec.input_schema.get("properties", {}))
        required = set(spec.input_schema.get("required", []))
        unknown = set(arguments) - allowed
        missing = required - set(arguments)
        if unknown:
            raise ValueError(f"unknown tool arguments: {sorted(unknown)}")
        if missing:
            raise ValueError(f"missing tool arguments: {sorted(missing)}")
        if not PermissionManager().authorize(spec, granted, confirmed=confirmed):
            raise PermissionError(f"tool authorization denied: {name}")
        return function(**arguments)


class Planner:
    def create(self, goal: str, steps: list[PlanStep]) -> Plan:
        if not goal.strip():
            raise ValueError("plan goal cannot be empty")
        ids = {s.id for s in steps}
        for step in steps:
            if step.id in step.depends_on:
                raise ValueError("plan step cannot depend on itself")
            if any(dep not in ids for dep in step.depends_on):
                raise ValueError(f"unknown dependency for {step.id}")
        return Plan(goal=goal, steps=steps)


class Verifier:
    def verify(self, expected: Any, actual: Any) -> bool:
        return expected == actual


class RecoveryManager:
    TRANSIENT = {"timeout", "network", "rate_limit", "provider_unavailable"}

    def classify(self, error: Exception) -> str:
        name = type(error).__name__.lower()
        message = str(error).lower()
        for key in self.TRANSIENT:
            if key in name or key in message:
                return "transient"
        if isinstance(error, PermissionError):
            return "authorization"
        if isinstance(error, (ValueError, TypeError)):
            return "validation"
        return "permanent"

    def should_retry(self, error: Exception, retries: int, max_retries: int) -> bool:
        return self.classify(error) == "transient" and retries < max_retries


class Executor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def execute_step(
        self,
        run: AgentRun,
        definition: AgentDefinition,
        step: PlanStep,
        arguments: dict[str, Any],
        *,
        granted: set[Permission],
        confirmed: bool = False,
    ) -> Any:
        run.check_limits(definition)
        run.steps += 1
        if not step.tool:
            return None
        run.tool_calls += 1
        return self.registry.execute(step.tool, arguments, granted=granted, confirmed=confirmed)


class ContextManager:
    def __init__(self, max_items: int = 40) -> None:
        self.max_items = max(1, max_items)

    def bound(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return messages[-self.max_items:]


class ResponseSynthesizer:
    def synthesize(self, result: Any, *, verified: bool = False) -> str:
        if not verified:
            return "The operation completed internally, but its external result has not been verified."
        return str(result)


class ASTRAOrchestrator:
    def __init__(self, *, tools: ToolRegistry | None = None) -> None:
        self.tools = tools or ToolRegistry()
        self.permissions = PermissionManager()
        self.planner = Planner()
        self.executor = Executor(self.tools)
        self.verifier = Verifier()
        self.recovery = RecoveryManager()
        self.context = ContextManager()
        self.responses = ResponseSynthesizer()

    def build_plan(self, goal: str, steps: list[PlanStep]) -> Plan:
        return self.planner.create(goal, steps)

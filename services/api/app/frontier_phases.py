from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Protocol


class PhaseCapability(str, Enum):
    SOFTWARE = "21-software-engineering"
    VOICE = "22-voice"
    REALTIME = "23-real-time"
    SKILLS = "24-skills"
    EVALUATION = "25-evaluation"
    MODEL_ROUTING = "26-model-routing"
    HYBRID = "27-local-cloud-hybrid"
    DISTRIBUTED = "28-distributed-aethon"
    IOT = "29-iot-gateway"


class FrontierSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class CapabilityRequest:
    capability: PhaseCapability
    operation: str
    payload: dict[str, Any]
    requires_approval: bool = False


@dataclass(frozen=True)
class CapabilityResult:
    capability: PhaseCapability
    operation: str
    success: bool
    output: Any = None
    error: str = ""


class CapabilityAdapter(Protocol):
    def execute(self, request: CapabilityRequest) -> CapabilityResult: ...


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    expected: Any
    actual: Any


@dataclass(frozen=True)
class EvaluationReport:
    passed: int
    total: int
    score: float


class BoundedFrontierEngine:
    """Common safety/budget boundary for phases 21-29.

    Adapters perform real provider-specific work. This layer never invents
    provider execution and never treats model/tool output as authority.
    """

    def __init__(self, *, max_operations: int = 32, max_payload_items: int = 64, max_payload_text: int = 12000) -> None:
        if not 1 <= max_operations <= 256 or not 1 <= max_payload_items <= 10000 or not 1 <= max_payload_text <= 100000:
            raise ValueError("invalid frontier bounds")
        self.max_operations = max_operations
        self.max_payload_items = max_payload_items
        self.max_payload_text = max_payload_text

    def validate(self, requests: Iterable[CapabilityRequest]) -> tuple[CapabilityRequest, ...]:
        values = tuple(requests)
        if len(values) > self.max_operations:
            raise FrontierSecurityError("frontier operation budget exceeded")
        for request in values:
            if not isinstance(request.capability, PhaseCapability):
                raise FrontierSecurityError("unsupported capability")
            if not request.operation.strip() or len(request.operation) > 200:
                raise FrontierSecurityError("invalid operation")
            if len(request.payload) > self.max_payload_items:
                raise FrontierSecurityError("payload item limit exceeded")
            for key, value in request.payload.items():
                if len(str(key)) > 200 or len(str(value)) > self.max_payload_text:
                    raise FrontierSecurityError("payload text limit exceeded")
        return values

    def execute(self, requests: Iterable[CapabilityRequest], adapters: dict[PhaseCapability, CapabilityAdapter], *, approve: bool = False) -> tuple[CapabilityResult, ...]:
        results: list[CapabilityResult] = []
        for request in self.validate(requests):
            if request.requires_approval and not approve:
                results.append(CapabilityResult(request.capability, request.operation, False, error="approval required"))
                continue
            adapter = adapters.get(request.capability)
            if adapter is None:
                results.append(CapabilityResult(request.capability, request.operation, False, error="adapter unavailable"))
                continue
            result = adapter.execute(request)
            results.append(result)
            if not result.success:
                break
        return tuple(results)

    @staticmethod
    def evaluate(cases: Iterable[EvaluationCase]) -> EvaluationReport:
        values = tuple(cases)
        if not values:
            raise FrontierSecurityError("evaluation cases must not be empty")
        passed = sum(case.expected == case.actual for case in values)
        return EvaluationReport(passed, len(values), passed / len(values) * 100.0)


class SkillRegistry:
    """Deterministic, bounded skill metadata registry; registration is not authority."""

    def __init__(self, *, max_skills: int = 256) -> None:
        if not 1 <= max_skills <= 10000:
            raise ValueError("invalid skill bound")
        self.max_skills = max_skills
        self._skills: dict[str, dict[str, Any]] = {}

    def register(self, name: str, metadata: dict[str, Any]) -> None:
        key = name.strip()
        if not key or len(key) > 200:
            raise FrontierSecurityError("invalid skill name")
        if key not in self._skills and len(self._skills) >= self.max_skills:
            raise FrontierSecurityError("skill registry limit exceeded")
        self._skills[key] = dict(metadata)

    def get(self, name: str) -> dict[str, Any] | None:
        value = self._skills.get(name.strip())
        return dict(value) if value is not None else None

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._skills))


__all__ = ["BoundedFrontierEngine", "CapabilityAdapter", "CapabilityRequest", "CapabilityResult", "EvaluationCase", "EvaluationReport", "FrontierSecurityError", "PhaseCapability", "SkillRegistry"]
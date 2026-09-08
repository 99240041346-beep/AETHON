from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class ModelRoutingError(ValueError):
    pass


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    capabilities: tuple[str, ...] = ()
    priority: int = 50
    cost: float = 0.0
    latency_ms: int = 0
    requires_approval: bool = False


@dataclass(frozen=True)
class ModelRequest:
    task: str
    required_capabilities: tuple[str, ...] = ()
    max_cost: float | None = None
    max_latency_ms: int | None = None
    requires_approval: bool = False


@dataclass(frozen=True)
class ModelRoute:
    model: str
    reason: str
    requires_approval: bool


class ModelRouter:
    """Deterministic, bounded provider-neutral model routing policy."""

    def __init__(self, candidates: Iterable[ModelCandidate], *, max_candidates: int = 64, max_name: int = 256) -> None:
        if not 1 <= max_candidates <= 1000 or not 1 <= max_name <= 4096:
            raise ValueError("invalid routing bounds")
        values = tuple(candidates)
        if len(values) > max_candidates:
            raise ModelRoutingError("model candidate budget exceeded")
        seen: set[str] = set()
        normalized: list[ModelCandidate] = []
        for candidate in values:
            name = candidate.name.strip()
            if not name or len(name) > max_name:
                raise ModelRoutingError("invalid model name")
            key = name.casefold()
            if key in seen:
                raise ModelRoutingError("duplicate model candidate")
            seen.add(key)
            if not 0 <= candidate.priority <= 100 or candidate.cost < 0 or candidate.latency_ms < 0:
                raise ModelRoutingError("invalid model candidate limits")
            normalized.append(ModelCandidate(name, tuple(sorted({c.strip().casefold() for c in candidate.capabilities if c.strip()})), candidate.priority, candidate.cost, candidate.latency_ms, candidate.requires_approval))
        self.candidates = tuple(normalized)
        self.max_candidates = max_candidates

    def route(self, request: ModelRequest, *, approve: bool = False) -> ModelRoute:
        task = request.task.strip()
        if not task:
            raise ModelRoutingError("model task is required")
        if request.max_cost is not None and request.max_cost < 0:
            raise ModelRoutingError("max_cost must be non-negative")
        if request.max_latency_ms is not None and request.max_latency_ms < 0:
            raise ModelRoutingError("max_latency_ms must be non-negative")
        required = {c.strip().casefold() for c in request.required_capabilities if c.strip()}
        eligible = [c for c in self.candidates if required.issubset(c.capabilities) and (request.max_cost is None or c.cost <= request.max_cost) and (request.max_latency_ms is None or c.latency_ms <= request.max_latency_ms)]
        if request.requires_approval and not approve:
            raise ModelRoutingError("approval required")
        eligible = [c for c in eligible if not c.requires_approval or approve]
        if not eligible:
            raise ModelRoutingError("no eligible model candidate")
        selected = min(eligible, key=lambda c: (-c.priority, c.cost, c.latency_ms, c.name.casefold()))
        return ModelRoute(selected.name, "deterministic policy selection", selected.requires_approval)


__all__ = ["ModelCandidate", "ModelRequest", "ModelRoute", "ModelRouter", "ModelRoutingError"]

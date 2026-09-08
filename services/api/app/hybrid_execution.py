from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class HybridRoutingError(ValueError):
    pass


class ExecutionLocation(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    AUTO = "auto"


@dataclass(frozen=True)
class HybridRequest:
    task: str
    location: ExecutionLocation = ExecutionLocation.AUTO
    max_cost: float | None = None
    max_latency_ms: int | None = None
    requires_network: bool = False
    requires_approval: bool = False


@dataclass(frozen=True)
class ExecutionCandidate:
    name: str
    location: ExecutionLocation
    cost: float = 0.0
    latency_ms: int = 0
    network: bool = False
    requires_approval: bool = False
    priority: int = 50


@dataclass(frozen=True)
class HybridRoute:
    candidate: str
    location: ExecutionLocation
    reason: str
    requires_approval: bool


class HybridRouter:
    """Deterministic policy boundary for local/cloud execution placement."""

    def __init__(self, candidates: Iterable[ExecutionCandidate], *, max_candidates: int = 64) -> None:
        if not 1 <= max_candidates <= 1000:
            raise ValueError("invalid routing bounds")
        values = tuple(candidates)
        if len(values) > max_candidates:
            raise HybridRoutingError("execution candidate budget exceeded")
        seen: set[str] = set()
        normalized: list[ExecutionCandidate] = []
        for candidate in values:
            name = candidate.name.strip()
            if not name or name.casefold() in seen:
                raise HybridRoutingError("invalid or duplicate execution candidate")
            if candidate.location not in (ExecutionLocation.LOCAL, ExecutionLocation.CLOUD):
                raise HybridRoutingError("candidate location must be local or cloud")
            if candidate.cost < 0 or candidate.latency_ms < 0 or not 0 <= candidate.priority <= 100:
                raise HybridRoutingError("invalid execution candidate limits")
            seen.add(name.casefold())
            normalized.append(ExecutionCandidate(name, candidate.location, candidate.cost, candidate.latency_ms, candidate.network, candidate.requires_approval, candidate.priority))
        self.candidates = tuple(normalized)

    def route(self, request: HybridRequest, *, approve_network: bool = False) -> HybridRoute:
        if not request.task.strip():
            raise HybridRoutingError("execution task is required")
        if request.max_cost is not None and request.max_cost < 0:
            raise HybridRoutingError("max_cost must be non-negative")
        if request.max_latency_ms is not None and request.max_latency_ms < 0:
            raise HybridRoutingError("max_latency_ms must be non-negative")
        if request.requires_network and not approve_network:
            raise HybridRoutingError("network approval required")
        allowed_locations = {ExecutionLocation.LOCAL, ExecutionLocation.CLOUD} if request.location == ExecutionLocation.AUTO else {request.location}
        eligible = [c for c in self.candidates if c.location in allowed_locations and (not request.requires_network or c.network) and (request.max_cost is None or c.cost <= request.max_cost) and (request.max_latency_ms is None or c.latency_ms <= request.max_latency_ms) and (approve_network or not c.requires_approval)]
        if not eligible:
            raise HybridRoutingError("no eligible execution candidate")
        selected = min(eligible, key=lambda c: (-c.priority, c.cost, c.latency_ms, c.name.casefold()))
        return HybridRoute(selected.name, selected.location, "deterministic local/cloud policy selection", selected.requires_approval)


__all__ = ["ExecutionLocation", "ExecutionCandidate", "HybridRequest", "HybridRoute", "HybridRouter", "HybridRoutingError"]

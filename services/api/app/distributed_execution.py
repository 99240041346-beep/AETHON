from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class DistributedRoutingError(ValueError):
    pass


@dataclass(frozen=True)
class DistributedRequest:
    task: str
    required_capabilities: tuple[str, ...] = ()
    preferred_region: str | None = None
    max_cost: float | None = None
    max_latency_ms: int | None = None
    requires_approval: bool = False


@dataclass(frozen=True)
class DistributedCandidate:
    name: str
    capabilities: tuple[str, ...] = ()
    region: str = "local"
    cost: float = 0.0
    latency_ms: int = 0
    load: int = 0
    priority: int = 50
    requires_approval: bool = False


@dataclass(frozen=True)
class DistributedRoute:
    candidate: str
    region: str
    reason: str
    requires_approval: bool


class DistributedRouter:
    """Deterministic, bounded node-selection policy; it never executes remotely."""

    def __init__(self, candidates: Iterable[DistributedCandidate], *, max_candidates: int = 64) -> None:
        if not 1 <= max_candidates <= 1000:
            raise ValueError("invalid routing bounds")
        values = tuple(candidates)
        if len(values) > max_candidates:
            raise DistributedRoutingError("distributed candidate budget exceeded")
        seen: set[str] = set()
        normalized: list[DistributedCandidate] = []
        for candidate in values:
            name = candidate.name.strip()
            if not name or name.casefold() in seen:
                raise DistributedRoutingError("invalid or duplicate distributed candidate")
            region = candidate.region.strip().casefold()
            if not region:
                raise DistributedRoutingError("candidate region is required")
            if candidate.cost < 0 or candidate.latency_ms < 0 or not 0 <= candidate.load <= 100 or not 0 <= candidate.priority <= 100:
                raise DistributedRoutingError("invalid distributed candidate limits")
            capabilities = tuple(sorted({c.strip().casefold() for c in candidate.capabilities if c.strip()}))
            seen.add(name.casefold())
            normalized.append(DistributedCandidate(name, capabilities, region, candidate.cost, candidate.latency_ms, candidate.load, candidate.priority, candidate.requires_approval))
        self.candidates = tuple(normalized)

    def route(self, request: DistributedRequest, *, approve: bool = False) -> DistributedRoute:
        if not request.task.strip():
            raise DistributedRoutingError("distributed task is required")
        if request.max_cost is not None and request.max_cost < 0:
            raise DistributedRoutingError("max_cost must be non-negative")
        if request.max_latency_ms is not None and request.max_latency_ms < 0:
            raise DistributedRoutingError("max_latency_ms must be non-negative")
        if request.requires_approval and not approve:
            raise DistributedRoutingError("approval required")
        required = {c.strip().casefold() for c in request.required_capabilities if c.strip()}
        preferred = request.preferred_region.strip().casefold() if request.preferred_region else None
        eligible = [
            c for c in self.candidates
            if required.issubset(c.capabilities)
            and (preferred is None or c.region == preferred)
            and (request.max_cost is None or c.cost <= request.max_cost)
            and (request.max_latency_ms is None or c.latency_ms <= request.max_latency_ms)
            and (approve or not c.requires_approval)
        ]
        if not eligible:
            raise DistributedRoutingError("no eligible distributed candidate")
        selected = min(eligible, key=lambda c: (-c.priority, c.load, c.cost, c.latency_ms, c.name.casefold()))
        return DistributedRoute(selected.name, selected.region, "deterministic distributed policy selection", selected.requires_approval)


__all__ = ["DistributedCandidate", "DistributedRequest", "DistributedRoute", "DistributedRouter", "DistributedRoutingError"]

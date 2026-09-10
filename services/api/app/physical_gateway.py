from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class PhysicalGatewayError(ValueError):
    pass


class PhysicalOperation(str, Enum):
    READ = "read"
    WRITE = "write"
    ACTUATE = "actuate"
    STOP = "stop"


@dataclass(frozen=True)
class PhysicalRequest:
    operation: PhysicalOperation
    target: str
    payload: str = ""
    requires_approval: bool = False


@dataclass(frozen=True)
class PhysicalCandidate:
    name: str
    operations: tuple[PhysicalOperation, ...] = ()
    requires_approval: bool = False
    priority: int = 50


@dataclass(frozen=True)
class PhysicalRoute:
    candidate: str
    operation: PhysicalOperation
    target: str
    requires_approval: bool


class PhysicalGateway:
    """Bounded policy boundary for physical-world operations; never drives hardware."""

    def __init__(self, candidates: Iterable[PhysicalCandidate], *, max_candidates: int = 64, max_payload: int = 20000) -> None:
        if not 1 <= max_candidates <= 1000 or not 1 <= max_payload <= 100000:
            raise ValueError("invalid gateway bounds")
        values = tuple(candidates)
        if len(values) > max_candidates:
            raise PhysicalGatewayError("physical candidate budget exceeded")
        seen: set[str] = set()
        normalized: list[PhysicalCandidate] = []
        for candidate in values:
            name = candidate.name.strip()
            if not name or name.casefold() in seen:
                raise PhysicalGatewayError("invalid or duplicate physical candidate")
            if not 0 <= candidate.priority <= 100:
                raise PhysicalGatewayError("invalid physical candidate priority")
            operations = tuple(dict.fromkeys(candidate.operations))
            if not operations or any(op not in PhysicalOperation for op in operations):
                raise PhysicalGatewayError("invalid physical candidate operations")
            seen.add(name.casefold())
            normalized.append(PhysicalCandidate(name, operations, candidate.requires_approval, candidate.priority))
        self.candidates = tuple(normalized)
        self.max_payload = max_payload

    def route(self, request: PhysicalRequest, *, approve: bool = False) -> PhysicalRoute:
        target = request.target.strip()
        if not target:
            raise PhysicalGatewayError("physical target is required")
        if len(request.payload) > self.max_payload:
            raise PhysicalGatewayError("physical payload budget exceeded")
        if request.requires_approval and not approve:
            raise PhysicalGatewayError("approval required")
        eligible = [
            c for c in self.candidates
            if request.operation in c.operations and (approve or not c.requires_approval)
        ]
        if not eligible:
            raise PhysicalGatewayError("no eligible physical candidate")
        selected = min(eligible, key=lambda c: (-c.priority, c.name.casefold()))
        return PhysicalRoute(selected.name, request.operation, target, selected.requires_approval)


__all__ = ["PhysicalGateway", "PhysicalCandidate", "PhysicalOperation", "PhysicalRequest", "PhysicalRoute", "PhysicalGatewayError"]

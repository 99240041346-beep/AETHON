from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol


class RealtimeOperation(str, Enum):
    PUBLISH = "publish"
    SUBSCRIBE = "subscribe"
    SEND = "send"
    CLOSE = "close"


class RealtimeSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class RealtimeRequest:
    operation: RealtimeOperation
    channel: str = ""
    payload: str = ""
    requires_approval: bool = False


@dataclass(frozen=True)
class RealtimeResult:
    operation: RealtimeOperation
    success: bool
    payload: str = ""
    error: str = ""


class RealtimeAdapter(Protocol):
    def execute(self, request: RealtimeRequest) -> RealtimeResult: ...


class BoundedRealtimeAgent:
    """Provider-neutral realtime policy boundary; adapters own network transport."""

    def __init__(self, *, max_operations: int = 32, max_channel: int = 256, max_payload: int = 12000) -> None:
        if not 1 <= max_operations <= 128 or not 1 <= max_channel <= 4096 or not 1 <= max_payload <= 100000:
            raise ValueError("invalid realtime bounds")
        self.max_operations = max_operations
        self.max_channel = max_channel
        self.max_payload = max_payload

    def validate_requests(self, requests: Iterable[RealtimeRequest]) -> tuple[RealtimeRequest, ...]:
        values = tuple(requests)
        if len(values) > self.max_operations:
            raise RealtimeSecurityError("realtime operation budget exceeded")
        for request in values:
            if not isinstance(request.operation, RealtimeOperation):
                raise RealtimeSecurityError("unsupported realtime operation")
            if len(request.channel.strip()) > self.max_channel:
                raise RealtimeSecurityError("realtime channel exceeds bounds")
            if len(request.payload) > self.max_payload:
                raise RealtimeSecurityError("realtime payload exceeds bounds")
            if request.operation is not RealtimeOperation.CLOSE and not request.channel.strip():
                raise RealtimeSecurityError("realtime channel is required")
            if request.operation in (RealtimeOperation.PUBLISH, RealtimeOperation.SEND) and not request.payload:
                raise RealtimeSecurityError("realtime payload is required")
        return values

    def execute(self, requests: Iterable[RealtimeRequest], adapter: RealtimeAdapter, *, approve: bool = False) -> tuple[RealtimeResult, ...]:
        results: list[RealtimeResult] = []
        for request in self.validate_requests(requests):
            if request.requires_approval and not approve:
                results.append(RealtimeResult(request.operation, False, error="approval required"))
                continue
            result = adapter.execute(request)
            results.append(result)
            if not result.success:
                break
        return tuple(results)

    def plan(self, goal: str) -> tuple[RealtimeRequest, ...]:
        if not goal.strip():
            raise RealtimeSecurityError("realtime goal is required")
        return (RealtimeRequest(RealtimeOperation.CLOSE),)


__all__ = ["BoundedRealtimeAgent", "RealtimeAdapter", "RealtimeOperation", "RealtimeRequest", "RealtimeResult", "RealtimeSecurityError"]

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Protocol


class VoiceOperation(str, Enum):
    TRANSCRIBE = "transcribe"
    SYNTHESIZE = "synthesize"
    STOP = "stop"


class VoiceSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class VoiceRequest:
    operation: VoiceOperation
    text: str = ""
    audio: bytes = b""
    requires_approval: bool = False


@dataclass(frozen=True)
class VoiceResult:
    operation: VoiceOperation
    success: bool
    text: str = ""
    audio: bytes = b""
    error: str = ""


class VoiceAdapter(Protocol):
    def execute(self, request: VoiceRequest) -> VoiceResult: ...


class BoundedVoiceAgent:
    """Provider-neutral voice policy boundary; adapters perform real audio work."""

    def __init__(self, *, max_operations: int = 16, max_text: int = 12000, max_audio_bytes: int = 25 * 1024 * 1024) -> None:
        if not 1 <= max_operations <= 64 or not 1 <= max_text <= 100000 or not 1 <= max_audio_bytes <= 100 * 1024 * 1024:
            raise ValueError("invalid voice bounds")
        self.max_operations = max_operations
        self.max_text = max_text
        self.max_audio_bytes = max_audio_bytes

    def validate_requests(self, requests: Iterable[VoiceRequest]) -> tuple[VoiceRequest, ...]:
        values = tuple(requests)
        if len(values) > self.max_operations:
            raise VoiceSecurityError("voice operation budget exceeded")
        for request in values:
            if not isinstance(request.operation, VoiceOperation):
                raise VoiceSecurityError("unsupported voice operation")
            if len(request.text) > self.max_text:
                raise VoiceSecurityError("voice text exceeds bounds")
            if len(request.audio) > self.max_audio_bytes:
                raise VoiceSecurityError("voice audio exceeds bounds")
            if request.operation is VoiceOperation.TRANSCRIBE and not request.audio:
                raise VoiceSecurityError("transcription audio is required")
            if request.operation is VoiceOperation.SYNTHESIZE and not request.text.strip():
                raise VoiceSecurityError("synthesis text is required")
        return values

    def execute(self, requests: Iterable[VoiceRequest], adapter: VoiceAdapter, *, approve: bool = False) -> tuple[VoiceResult, ...]:
        results: list[VoiceResult] = []
        for request in self.validate_requests(requests):
            if request.requires_approval and not approve:
                results.append(VoiceResult(request.operation, False, error="approval required"))
                continue
            result = adapter.execute(request)
            results.append(result)
            if not result.success:
                break
        return tuple(results)

    def plan(self, goal: str) -> tuple[VoiceRequest, ...]:
        if not goal.strip():
            raise VoiceSecurityError("voice goal is required")
        return (VoiceRequest(VoiceOperation.STOP),)


__all__ = ["BoundedVoiceAgent", "VoiceAdapter", "VoiceOperation", "VoiceRequest", "VoiceResult", "VoiceSecurityError"]

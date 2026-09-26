from __future__ import annotations

from dataclasses import dataclass
import re

@dataclass(frozen=True)
class MemoryCandidate:
    content: str
    explicit: bool
    sensitive: bool
    reason: str

class MemoryPolicy:
    _SENSITIVE = re.compile(r"\b(password|passcode|otp|one[- ]time password|api key|secret|credit card|bank account|aadhaar|passport)\b", re.I)
    _EXPLICIT = re.compile(r"\b(remember|save this|store this|don't forget)\b", re.I)

    def extract(self, text: str) -> MemoryCandidate | None:
        value = text.strip()
        if not value:
            return None
        explicit = bool(self._EXPLICIT.search(value))
        if not explicit:
            return None
        sensitive = bool(self._SENSITIVE.search(value))
        if sensitive:
            return MemoryCandidate(value, True, True, "sensitive content requires explicit policy handling")
        return MemoryCandidate(value, True, False, "explicit user memory request")

    def can_store(self, candidate: MemoryCandidate, *, sensitive_storage_enabled: bool = False) -> bool:
        return candidate.explicit and (not candidate.sensitive or sensitive_storage_enabled)

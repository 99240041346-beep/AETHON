from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class LearningSignal:
    """A bounded, auditable signal derived from verified task outcomes."""

    kind: str
    value: str
    confidence: float = 0.5


class AgentLearning:
    """Extract small deterministic learning signals without changing safety policy."""

    def __init__(self, *, max_signals: int = 5, max_chars: int = 500) -> None:
        if not 1 <= max_signals <= 20:
            raise ValueError("max_signals must be between 1 and 20")
        if not 100 <= max_chars <= 5000:
            raise ValueError("max_chars must be between 100 and 5000")
        self.max_signals = max_signals
        self.max_chars = max_chars

    def from_outcome(self, *, goal: str, result: object, verified: bool) -> tuple[LearningSignal, ...]:
        if not verified:
            return ()
        text = str(result).strip()
        if not text:
            return ()
        return (LearningSignal("verified_outcome", f"Goal: {goal.strip()}\nResult: {text[:self.max_chars]}", 1.0),)

    def deduplicate(self, signals: Iterable[LearningSignal]) -> tuple[LearningSignal, ...]:
        result: list[LearningSignal] = []
        seen: set[tuple[str, str]] = set()
        for signal in signals:
            key = (signal.kind, signal.value.casefold())
            if key in seen:
                continue
            seen.add(key)
            result.append(signal)
            if len(result) >= self.max_signals:
                break
        return tuple(result)

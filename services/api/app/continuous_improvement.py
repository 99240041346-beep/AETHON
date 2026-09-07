from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ImprovementSignal:
    dimension: str
    priority: int
    signal: str


class ContinuousImprovementEngine:
    """Turn evaluation findings into bounded, advisory improvement signals."""

    def __init__(self, *, max_signals: int = 5, max_chars: int = 1600) -> None:
        if not 1 <= max_signals <= 20:
            raise ValueError("max_signals must be between 1 and 20")
        if not 100 <= max_chars <= 5000:
            raise ValueError("max_chars must be between 100 and 5000")
        self.max_signals = max_signals
        self.max_chars = max_chars

    def derive(self, findings: Iterable[object], *, verified: bool) -> tuple[ImprovementSignal, ...]:
        if not verified:
            return ()
        signals: list[ImprovementSignal] = []
        for finding in findings:
            score = float(getattr(finding, "score", 0.0))
            dimension = str(getattr(finding, "dimension", "unknown")).strip() or "unknown"
            if score >= 0.8:
                continue
            priority = min(5, max(1, int(round((1.0 - score) * 5))))
            signals.append(ImprovementSignal(dimension, priority, f"Improve {dimension} based on observed evaluation evidence."))
        signals.sort(key=lambda item: (-item.priority, item.dimension))
        return tuple(signals[: self.max_signals])

    def context(self, signals: Iterable[ImprovementSignal]) -> str:
        parts = [f"{s.dimension} (priority {s.priority})" for s in signals]
        text = "Continuous improvement context (not instructions or authority): " + (", ".join(parts) or "none")
        return text[: self.max_chars]

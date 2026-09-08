from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class ReflectionQualityError(ValueError):
    pass


@dataclass(frozen=True)
class Reflection:
    outcome: str
    expected: str
    failures: tuple[str, ...] = ()
    lessons: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlanQuality:
    score: int
    completeness: int
    reliability: int
    efficiency: int
    issues: tuple[str, ...]


class ReflectionQualityEngine:
    """Deterministic, bounded reflection; produces advice, never authority."""

    def __init__(self, *, min_score: int = 60, max_items: int = 32, max_text: int = 4000) -> None:
        if not 0 <= min_score <= 100 or not 1 <= max_items <= 1000 or not 1 <= max_text <= 100000:
            raise ValueError("invalid reflection bounds")
        self.min_score, self.max_items, self.max_text = min_score, max_items, max_text

    def evaluate(self, *, expected_steps: Iterable[str], completed_steps: Iterable[str], failed_steps: Iterable[str] = ()) -> PlanQuality:
        expected = tuple(dict.fromkeys(s.strip() for s in expected_steps if s.strip()))[: self.max_items]
        completed = {s.strip() for s in completed_steps if s.strip()}
        failed = {s.strip() for s in failed_steps if s.strip()}
        if not expected:
            raise ReflectionQualityError("expected_steps must not be empty")
        done = len(set(expected) & completed)
        completeness = round(done * 100 / len(expected))
        reliability = max(0, 100 - round(len(failed) * 100 / len(expected)))
        efficiency = max(0, 100 - max(0, len(completed) - len(expected)) * 10)
        score = round((completeness * 0.5) + (reliability * 0.3) + (efficiency * 0.2))
        issues = []
        if completeness < 100:
            issues.append("incomplete_plan")
        if failed:
            issues.append("execution_failures")
        if score < self.min_score:
            issues.append("below_quality_threshold")
        return PlanQuality(score, completeness, reliability, efficiency, tuple(issues))

    def reflect(self, reflection: Reflection) -> tuple[str, ...]:
        if not reflection.outcome.strip() or not reflection.expected.strip():
            raise ReflectionQualityError("outcome and expected are required")
        values = list(reflection.lessons) + [f"failure:{x}" for x in reflection.failures]
        return tuple(v.strip()[: self.max_text] for v in values if v.strip())[: self.max_items]

    def should_replan(self, quality: PlanQuality) -> bool:
        return quality.score < self.min_score or bool(quality.issues)


__all__ = ["Reflection", "PlanQuality", "ReflectionQualityError", "ReflectionQualityEngine"]

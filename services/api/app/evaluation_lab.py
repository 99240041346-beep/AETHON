from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


class EvaluationError(ValueError):
    pass


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    expected: str
    actual: str
    passed: bool
    score: int


@dataclass(frozen=True)
class EvaluationReport:
    cases: tuple[EvaluationCase, ...]
    score: int
    passed: int
    failed: int


class BoundedEvaluationLab:
    """Deterministic, bounded evaluation harness; evaluation never grants authority."""

    def __init__(self, *, max_cases: int = 256, max_text: int = 20000) -> None:
        if not 1 <= max_cases <= 5000 or not 1 <= max_text <= 100000:
            raise ValueError("invalid evaluation bounds")
        self.max_cases = max_cases
        self.max_text = max_text

    def evaluate(self, cases: Iterable[tuple[str, str, str]]) -> EvaluationReport:
        values = tuple(cases)
        if len(values) > self.max_cases:
            raise EvaluationError("evaluation case budget exceeded")
        results: list[EvaluationCase] = []
        for case_id, expected, actual in values:
            case_id = case_id.strip()
            expected = expected.strip()[: self.max_text]
            actual = actual.strip()[: self.max_text]
            if not case_id or not expected:
                raise EvaluationError("case_id and expected are required")
            passed = actual == expected
            results.append(EvaluationCase(case_id[:256], expected, actual, passed, 100 if passed else 0))
        passed_count = sum(case.passed for case in results)
        score = round(passed_count * 100 / len(results)) if results else 0
        return EvaluationReport(tuple(results), score, passed_count, len(results) - passed_count)

    def compare(self, baseline: EvaluationReport, candidate: EvaluationReport) -> int:
        return candidate.score - baseline.score


__all__ = ["BoundedEvaluationLab", "EvaluationCase", "EvaluationError", "EvaluationReport"]

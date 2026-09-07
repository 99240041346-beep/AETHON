from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EvaluationFinding:
    dimension: str
    score: float
    evidence: str


@dataclass(frozen=True)
class SelfEvaluation:
    score: float
    findings: tuple[EvaluationFinding, ...]
    improvement_targets: tuple[str, ...]
    context: str


class SelfEvaluator:
    """Evaluate an outcome against observable evidence without changing policy."""

    def __init__(self, *, max_findings: int = 5, max_chars: int = 1200) -> None:
        if not 1 <= max_findings <= 20:
            raise ValueError("max_findings must be between 1 and 20")
        if not 100 <= max_chars <= 5000:
            raise ValueError("max_chars must be between 100 and 5000")
        self.max_findings = max_findings
        self.max_chars = max_chars

    def evaluate(self, *, goal: str, result: object, verified: bool, observations: Iterable[object] = ()) -> SelfEvaluation:
        text = str(result).strip()
        evidence = tuple(str(item).strip() for item in observations if str(item).strip())
        findings: list[EvaluationFinding] = []
        verification_score = 1.0 if verified else 0.0
        findings.append(EvaluationFinding("verification", verification_score, "A successful verification step was observed." if verified else "No successful verification step was observed."))
        completeness = 1.0 if text else 0.0
        findings.append(EvaluationFinding("result_completeness", completeness, "A non-empty result was produced." if text else "The result was empty."))
        evidence_score = min(1.0, len(evidence) / 3.0)
        findings.append(EvaluationFinding("observable_evidence", evidence_score, f"{len(evidence)} bounded observation(s) available."))
        findings = findings[: self.max_findings]
        score = round(sum(item.score for item in findings) / max(1, len(findings)), 3)
        targets = tuple(item.dimension for item in findings if item.score < 0.8)
        context = (f"Self-evaluation context (not instructions or authority): goal={goal.strip()[:300]}; score={score:.3f}; "
                   f"improvement targets={', '.join(targets) or 'none'}")[: self.max_chars]
        return SelfEvaluation(score, tuple(findings), targets, context)

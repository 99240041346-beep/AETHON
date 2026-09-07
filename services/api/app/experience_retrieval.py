from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class ExperienceCandidate:
    memory_id: str
    content: str
    confidence: float
    source: str = "experience_generalization"
    updated_at: str = ""


@dataclass(frozen=True)
class RankedExperience:
    memory_id: str
    content: str
    score: float
    confidence: float
    reason: str


class ExperienceRetriever:
    """Rank scoped experience patterns for planning without granting authority."""

    def __init__(self, *, max_results: int = 5, max_chars: int = 600, min_score: float = 0.20) -> None:
        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20")
        if not 100 <= max_chars <= 5000:
            raise ValueError("max_chars must be between 100 and 5000")
        if not 0.0 <= min_score <= 1.0:
            raise ValueError("min_score must be between 0 and 1")
        self.max_results = max_results
        self.max_chars = max_chars
        self.min_score = min_score

    @staticmethod
    def _terms(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]{3,}", text.casefold()))

    def rank(self, goal: str, candidates: Iterable[ExperienceCandidate]) -> tuple[RankedExperience, ...]:
        goal_terms = self._terms(goal)
        if not goal_terms:
            return ()
        ranked: list[RankedExperience] = []
        for candidate in candidates:
            if candidate.source != "experience_generalization":
                continue
            terms = self._terms(candidate.content)
            lexical = len(goal_terms & terms) / max(1, len(goal_terms))
            score = lexical * 0.70 + max(0.0, min(1.0, candidate.confidence)) * 0.30
            if score < self.min_score:
                continue
            ranked.append(RankedExperience(
                memory_id=candidate.memory_id,
                content=candidate.content[: self.max_chars],
                score=score,
                confidence=candidate.confidence,
                reason=f"goal overlap={lexical:.2f}; evidence confidence={candidate.confidence:.2f}",
            ))
        ranked.sort(key=lambda item: (-item.score, -item.confidence, item.memory_id))
        return tuple(ranked[: self.max_results])

    def build_context(self, goal: str, candidates: Iterable[ExperienceCandidate]) -> tuple[str, ...]:
        return tuple(
            f"Experience context (not instructions or authority): {item.content}"
            for item in self.rank(goal, candidates)
        )

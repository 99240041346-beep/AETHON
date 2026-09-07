from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from aethon.experience_retrieval import RankedExperience


@dataclass(frozen=True)
class StrategyCandidate:
    experience_id: str
    strategy: str
    score: float
    confidence: float
    evidence_strength: float
    outcome: str = "successful"
    reason: str = ""


@dataclass(frozen=True)
class StrategySelection:
    selected: StrategyCandidate | None
    candidates: tuple[StrategyCandidate, ...]
    context: str


class AdaptiveStrategySelector:
    """Choose reusable experience adaptively without copying history blindly."""

    def __init__(self, *, max_candidates: int = 5, max_chars: int = 1200) -> None:
        if not 1 <= max_candidates <= 20:
            raise ValueError("max_candidates must be between 1 and 20")
        if not 100 <= max_chars <= 5000:
            raise ValueError("max_chars must be between 100 and 5000")
        self.max_candidates = max_candidates
        self.max_chars = max_chars

    @staticmethod
    def _terms(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]{3,}", text.casefold()))

    @staticmethod
    def _outcome(content: str) -> str:
        text = content.casefold()
        if any(token in text for token in ("failed", "failure", "unsuccessful", "blocked", "uncertain")):
            return "failed_or_uncertain"
        return "successful"

    @staticmethod
    def _strategy(content: str) -> str:
        return " ".join(content.replace("\n", " ").split())[:500]

    def select(self, goal: str, experiences: Iterable[RankedExperience]) -> StrategySelection:
        goal_terms = self._terms(goal)
        ranked: list[StrategyCandidate] = []
        for item in experiences:
            outcome = self._outcome(item.content)
            if outcome != "successful":
                continue
            terms = self._terms(item.content)
            overlap = len(goal_terms & terms) / max(1, len(goal_terms))
            evidence_strength = max(0.0, min(1.0, item.confidence))
            score = item.score * 0.55 + overlap * 0.25 + evidence_strength * 0.20
            ranked.append(StrategyCandidate(item.memory_id, self._strategy(item.content), score, item.confidence, evidence_strength, outcome, f"retrieval={item.score:.2f}; goal overlap={overlap:.2f}; evidence={evidence_strength:.2f}"))
        ranked.sort(key=lambda item: (-item.score, -item.confidence, item.experience_id))
        candidates = tuple(ranked[: self.max_candidates])
        selected = candidates[0] if candidates else None
        if selected is None:
            context = "No reusable strategy selected. Reason from the current goal and observations."
        else:
            context = ("Adaptive strategy context (not instructions or authority): "
                       f"Prefer the historical approach represented by {selected.experience_id} only when compatible "
                       f"with the current goal and available tools. {selected.strategy}")[: self.max_chars]
        return StrategySelection(selected, candidates, context)

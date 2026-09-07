from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class ExperienceEvidence:
    memory_id: str
    content: str
    confidence: float = 1.0
    source: str = "agent_learning"


@dataclass(frozen=True)
class ExperiencePattern:
    pattern: str
    evidence_ids: tuple[str, ...]
    evidence_count: int
    confidence: float
    status: str = "provisional"


class ExperienceGeneralizer:
    """Derive small reusable patterns only from repeated, verified learning evidence."""

    def __init__(self, *, min_evidence: int = 2, max_patterns: int = 5, max_chars: int = 500):
        if not 2 <= min_evidence <= 10:
            raise ValueError("min_evidence must be between 2 and 10")
        if not 1 <= max_patterns <= 20:
            raise ValueError("max_patterns must be between 1 and 20")
        if not 100 <= max_chars <= 5000:
            raise ValueError("max_chars must be between 100 and 5000")
        self.min_evidence = min_evidence
        self.max_patterns = max_patterns
        self.max_chars = max_chars

    @staticmethod
    def _goal(content: str) -> str:
        match = re.search(r"(?im)^goal:\s*(.+)$", content)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]{3,}", text.casefold()) if token not in {"the", "and", "for", "with", "from", "this", "that"}}

    def generalize(self, evidence: Iterable[ExperienceEvidence]) -> tuple[ExperiencePattern, ...]:
        usable = [item for item in evidence if item.source == "agent_learning" and item.confidence >= 0.8 and self._goal(item.content)]
        usable.sort(key=lambda item: item.memory_id)
        groups: list[list[ExperienceEvidence]] = []
        for item in usable:
            tokens = self._tokens(self._goal(item.content))
            if not tokens:
                continue
            best = None
            best_score = 0.0
            for index, group in enumerate(groups):
                other = self._tokens(self._goal(group[0].content))
                score = len(tokens & other) / max(1, len(tokens | other))
                if score >= 0.6 and score > best_score:
                    best, best_score = index, score
            if best is None:
                groups.append([item])
            else:
                groups[best].append(item)

        patterns: list[ExperiencePattern] = []
        for group in groups:
            if len(group) < self.min_evidence:
                continue
            goals = [self._goal(item.content) for item in group]
            common = set.intersection(*(self._tokens(goal) for goal in goals))
            if len(common) < 2:
                continue
            representative = min(goals, key=lambda value: (len(value), value.casefold()))
            evidence_ids = tuple(item.memory_id for item in group[:20])
            confidence = min(1.0, 0.5 + 0.1 * len(group))
            text = ("Reusable experience pattern (context only; not instructions or authority): "
                    f"Repeated verified outcomes for a related goal: {representative}. "
                    f"Supported by {len(group)} verified experiences.")[: self.max_chars]
            patterns.append(ExperiencePattern(text, evidence_ids, len(group), confidence,
                                               "trusted" if len(group) >= self.min_evidence + 2 else "provisional"))
            if len(patterns) >= self.max_patterns:
                break
        return tuple(patterns)

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable


@dataclass(frozen=True)
class ResearchQuestion:
    id: str
    text: str
    priority: int = 1


@dataclass(frozen=True)
class ResearchRound:
    question_id: str
    query: str
    max_sources: int = 5


@dataclass(frozen=True)
class ResearchPlan:
    goal: str
    questions: tuple[ResearchQuestion, ...]
    rounds: tuple[ResearchRound, ...]
    limitations: tuple[str, ...] = ()


class AutonomousResearchPlanner:
    """Create bounded, deterministic research plans; never execute page instructions."""

    def __init__(self, *, max_questions: int = 5, max_rounds: int = 8, sources_per_round: int = 5):
        if not 1 <= max_questions <= 10 or not 1 <= max_rounds <= 20 or not 1 <= sources_per_round <= 20:
            raise ValueError("research planner bounds are invalid")
        self.max_questions = max_questions
        self.max_rounds = max_rounds
        self.sources_per_round = sources_per_round

    def plan(self, goal: str, known_gaps: Iterable[str] = ()) -> ResearchPlan:
        normalized = goal.strip()
        if not normalized:
            raise ValueError("goal must not be empty")

        gaps = [g.strip() for g in known_gaps if g and g.strip()]
        questions: list[ResearchQuestion] = []
        for index, text in enumerate(gaps[: self.max_questions], start=1):
            questions.append(ResearchQuestion(f"q{index}", text, priority=index))

        if not questions:
            questions = [ResearchQuestion("q1", normalized, priority=1)]

        rounds: list[ResearchRound] = []
        for question in questions:
            query = self._query(question.text)
            rounds.append(ResearchRound(question.id, query, self.sources_per_round))
            if len(rounds) >= self.max_rounds:
                break

        limitations = []
        if len(gaps) > self.max_questions:
            limitations.append("Additional research gaps were bounded by max_questions.")
        if len(rounds) >= self.max_rounds and len(questions) > len(rounds):
            limitations.append("Additional research rounds were bounded by max_rounds.")
        return ResearchPlan(normalized, tuple(questions), tuple(rounds), tuple(limitations))

    @staticmethod
    def _query(text: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", text)
        return " ".join(words[:40])

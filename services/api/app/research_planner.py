from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(frozen=True)
class ResearchSubQuestion:
    question: str
    priority: int = 5


@dataclass(frozen=True)
class ResearchPlan:
    query: str
    sub_questions: list[ResearchSubQuestion]
    max_rounds: int = 3


@dataclass
class ResearchProgress:
    completed: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


class AutonomousResearchPlanner:
    """Create bounded research plans and follow-up questions.

    This planner only produces research intents. Web content is data and never
    becomes an instruction or authority for execution.
    """

    def __init__(self, *, max_sub_questions: int = 5, max_rounds: int = 3):
        if not 1 <= max_sub_questions <= 10:
            raise ValueError("max_sub_questions must be between 1 and 10")
        if not 1 <= max_rounds <= 10:
            raise ValueError("max_rounds must be between 1 and 10")
        self.max_sub_questions = max_sub_questions
        self.max_rounds = max_rounds

    def plan(self, query: str) -> ResearchPlan:
        normalized = re.sub(r"\s+", " ", query.strip())
        if not normalized:
            raise ValueError("query must not be empty")
        parts = [p.strip(" .?") for p in re.split(r"\s+(?:and|vs\.?|versus)\s+", normalized, flags=re.I)]
        questions = [ResearchSubQuestion(normalized, 1)]
        for part in parts[1:self.max_sub_questions]:
            if part:
                questions.append(ResearchSubQuestion(f"What evidence supports {part}?", min(10, len(questions) + 1)))
        if len(questions) == 1:
            questions.append(ResearchSubQuestion(f"What are the strongest limitations or counterclaims about {normalized}?", 2))
        return ResearchPlan(normalized, questions[:self.max_sub_questions], self.max_rounds)

    def follow_up_questions(self, plan: ResearchPlan, progress: ResearchProgress, *, round_number: int) -> list[str]:
        if round_number >= plan.max_rounds:
            return []
        seen = {q.lower() for q in progress.completed}
        candidates = [q.question for q in plan.sub_questions if q.question.lower() not in seen]
        candidates.extend(progress.unresolved[: self.max_sub_questions])
        return list(dict.fromkeys(candidates))[: self.max_sub_questions]

    @staticmethod
    def identify_gaps(expected_questions: list[str], answered_questions: list[str]) -> list[str]:
        answered = {re.sub(r"\W+", " ", q).strip().lower() for q in answered_questions}
        return [q for q in expected_questions if re.sub(r"\W+", " ", q).strip().lower() not in answered]

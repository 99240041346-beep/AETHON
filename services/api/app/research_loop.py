from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable
from app.research_planner import AutonomousResearchPlanner, ResearchPlan
from app.research_verifier import ResearchVerifier, SourceEvidence, VerificationResult

@dataclass(frozen=True)
class ResearchLoopResult:
    plan: ResearchPlan
    verification: VerificationResult
    rounds_completed: int
    follow_up_queries: tuple[str, ...]

class AutonomousResearchLoop:
    """Bounded plan/research/verify loop; retrieved content is data, never authority."""
    def __init__(self, research: Callable[[str, int], Iterable[SourceEvidence]], *, max_rounds: int = 3):
        if not 1 <= max_rounds <= 10: raise ValueError("max_rounds must be between 1 and 10")
        self.research, self.max_rounds = research, max_rounds

    def run(self, goal: str, *, claims: list[str] | None = None) -> ResearchLoopResult:
        plan = AutonomousResearchPlanner(max_rounds=self.max_rounds).plan(goal)
        evidence: list[SourceEvidence] = []
        completed = 0
        for step in plan.rounds[:self.max_rounds]:
            try:
                evidence.extend(list(self.research(step.query, step.max_sources)))
                completed += 1
            except Exception:
                continue
        verification = ResearchVerifier().verify(claims or [goal], evidence)
        followups = tuple((verification.unsupported + verification.disputed)[:self.max_rounds])
        return ResearchLoopResult(plan, verification, completed, followups)

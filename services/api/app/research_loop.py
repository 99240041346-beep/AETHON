from __future__ import annotations

from dataclasses import dataclass

from app.research_planner import AutonomousResearchPlanner, ResearchPlan
from app.web_research import ResearchReport, WebResearchAgent


@dataclass(frozen=True)
class ResearchLoopResult:
    plan: ResearchPlan
    rounds: tuple[ResearchReport, ...]
    follow_up_queries: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]


class AutonomousResearchLoop:
    """Run bounded research rounds without executing retrieved web content."""

    def __init__(self, planner: AutonomousResearchPlanner, researcher: WebResearchAgent):
        self.planner = planner
        self.researcher = researcher

    def run(self, goal: str, *, max_questions: int = 5, max_rounds: int = 3) -> ResearchLoopResult:
        if not 1 <= max_questions <= 10:
            raise ValueError("max_questions must be between 1 and 10")
        if not 1 <= max_rounds <= 20:
            raise ValueError("max_rounds must be between 1 and 20")

        plan = self.planner.plan(goal)
        queries = [q.text for q in plan.questions[:max_questions]]
        reports: list[ResearchReport] = []
        gaps: list[str] = list(plan.limitations)
        followups: list[str] = []
        seen_queries: set[str] = set()

        for round_number in range(max_rounds):
            if not queries:
                break
            current = [q.strip() for q in queries if q and q.strip()]
            queries = []
            for query in current:
                key = query.casefold()
                if key in seen_queries:
                    continue
                seen_queries.add(key)
                try:
                    report = self.researcher.research(query)
                except Exception as exc:
                    gaps.append(f"research failure for '{query}': {type(exc).__name__}")
                    continue
                reports.append(report)
                gaps.extend(report.limitations)

                if report.limitations and round_number + 1 < max_rounds:
                    followups.append(f"verify unresolved aspects of: {query}")

            followups = list(dict.fromkeys(followups))
            if not followups:
                break
            queries = followups[:max_questions]
            followups = []

        return ResearchLoopResult(
            plan=plan,
            rounds=tuple(reports),
            follow_up_queries=tuple(queries),
            unresolved_gaps=tuple(dict.fromkeys(gaps)),
        )

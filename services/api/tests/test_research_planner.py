import pytest

from app.research_planner import AutonomousResearchPlanner, ResearchProgress


def test_plan_is_bounded_and_decomposes_comparison():
    planner = AutonomousResearchPlanner(max_sub_questions=3, max_rounds=2)
    plan = planner.plan("Python vs Rust for backend systems")
    assert len(plan.sub_questions) <= 3
    assert plan.max_rounds == 2


def test_followups_stop_at_round_limit():
    planner = AutonomousResearchPlanner(max_rounds=2)
    plan = planner.plan("AI safety")
    progress = ResearchProgress(completed=[])
    assert planner.follow_up_questions(plan, progress, round_number=2) == []


def test_gap_detection():
    gaps = AutonomousResearchPlanner.identify_gaps(["one", "two"], ["one"])
    assert gaps == ["two"]


def test_empty_query_rejected():
    with pytest.raises(ValueError):
        AutonomousResearchPlanner().plan(" ")

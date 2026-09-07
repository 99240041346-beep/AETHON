import pytest

from app.research_planner import AutonomousResearchPlanner


def test_empty_goal_rejected():
    with pytest.raises(ValueError):
        AutonomousResearchPlanner().plan(" ")


def test_goal_creates_bounded_round():
    plan = AutonomousResearchPlanner().plan("Compare retrieval systems")
    assert plan.goal == "Compare retrieval systems"
    assert len(plan.questions) == 1
    assert len(plan.rounds) == 1
    assert plan.rounds[0].query == "Compare retrieval systems"


def test_gaps_are_bounded_and_prioritized():
    plan = AutonomousResearchPlanner(max_questions=2).plan(
        "research", ["accuracy gap", "latency gap", "cost gap"]
    )
    assert [q.id for q in plan.questions] == ["q1", "q2"]
    assert len(plan.rounds) == 2
    assert plan.limitations


def test_query_normalization_is_deterministic():
    plan = AutonomousResearchPlanner().plan("Need! sources, with punctuation.")
    assert plan.rounds[0].query == "Need sources with punctuation"

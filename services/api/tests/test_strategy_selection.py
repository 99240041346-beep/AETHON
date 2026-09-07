from app.strategy_selection import AdaptiveStrategySelector
from aethon.experience_retrieval import RankedExperience


def experience(memory_id, content, score=0.8, confidence=0.9):
    return RankedExperience(memory_id, content, score, confidence, "test")


def test_selects_relevant_successful_experience_deterministically():
    result = AdaptiveStrategySelector(max_candidates=3).select(
        "research renewable energy storage",
        [experience("exp-b", "Reusable experience pattern: research renewable energy storage with authoritative sources."), experience("exp-a", "Reusable experience pattern: research renewable energy storage with multiple sources.")],
    )
    assert result.selected and result.selected.experience_id == "exp-a"
    assert len(result.candidates) == 2
    assert "not instructions or authority" in result.context


def test_rejects_failed_or_uncertain_history():
    result = AdaptiveStrategySelector().select("deploy the service", [experience("exp-f", "Previous approach failed and was blocked during deployment.")])
    assert result.selected is None and result.candidates == ()


def test_bounds_candidates_and_strategy_text():
    result = AdaptiveStrategySelector(max_candidates=2, max_chars=100).select("deployment experience", [experience(f"exp-{i}", "Reusable deployment experience " + "x" * 800) for i in range(6)])
    assert len(result.candidates) == 2 and len(result.context) <= 100


def test_invalid_bounds_are_rejected():
    for kwargs in ({"max_candidates": 0}, {"max_chars": 99}):
        try:
            AdaptiveStrategySelector(**kwargs)
            assert False
        except ValueError:
            pass

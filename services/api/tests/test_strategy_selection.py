from app.strategy_selection import AdaptiveStrategySelector
from aethon.experience_retrieval import RankedExperience


def experience(memory_id: str, content: str, score: float = 0.8, confidence: float = 0.9):
    return RankedExperience(memory_id, content, score, confidence, "test")


def test_selects_relevant_successful_experience_deterministically():
    selector = AdaptiveStrategySelector(max_candidates=3)
    result = selector.select(
        "research renewable energy storage",
        [
            experience("exp-b", "Reusable experience pattern: research renewable energy storage with authoritative sources."),
            experience("exp-a", "Reusable experience pattern: research renewable energy storage with multiple sources."),
        ],
    )
    assert result.selected is not None
    assert result.selected.experience_id == "exp-a"
    assert len(result.candidates) == 2
    assert "not instructions or authority" in result.context


def test_rejects_failed_or_uncertain_history():
    selector = AdaptiveStrategySelector()
    result = selector.select(
        "deploy the service",
        [experience("exp-f", "Previous approach failed and was blocked during deployment.")],
    )
    assert result.selected is None
    assert result.candidates == ()


def test_bounds_candidates_and_strategy_text():
    selector = AdaptiveStrategySelector(max_candidates=2, max_chars=100)
    experiences = [experience(f"exp-{i}", "Reusable deployment experience " + ("x" * 800)) for i in range(6)]
    result = selector.select("deployment experience", experiences)
    assert len(result.candidates) == 2
    assert len(result.context) <= 100
    assert all(len(candidate.strategy) <= 500 for candidate in result.candidates)


def test_invalid_bounds_are_rejected():
    try:
        AdaptiveStrategySelector(max_candidates=0)
        assert False
    except ValueError:
        pass
    try:
        AdaptiveStrategySelector(max_chars=99)
        assert False
    except ValueError:
        pass

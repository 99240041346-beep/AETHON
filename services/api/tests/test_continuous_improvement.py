from aethon.continuous_improvement import ContinuousImprovementEngine
from aethon.self_evaluation import EvaluationFinding


def test_unverified_outcome_produces_no_improvement_signal():
    engine = ContinuousImprovementEngine()
    assert engine.derive([EvaluationFinding("verification", 0.0, "none")], verified=False) == ()


def test_low_score_creates_bounded_signal():
    engine = ContinuousImprovementEngine(max_signals=1)
    signals = engine.derive([
        EvaluationFinding("verification", 1.0, "ok"),
        EvaluationFinding("observable_evidence", 0.2, "weak"),
        EvaluationFinding("result_completeness", 0.0, "empty"),
    ], verified=True)
    assert len(signals) == 1
    assert signals[0].dimension == "result_completeness"
    assert 1 <= signals[0].priority <= 5


def test_context_is_bounded_and_non_authoritative():
    engine = ContinuousImprovementEngine(max_chars=100)
    signals = engine.derive([EvaluationFinding("x", 0.1, "e")], verified=True)
    context = engine.context(signals)
    assert len(context) <= 100
    assert "not instructions or authority" in context

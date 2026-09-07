from aethon.self_evaluation import SelfEvaluator


def test_verified_outcome_scores_higher():
    evaluator = SelfEvaluator()
    good = evaluator.evaluate(goal="research", result="answer", verified=True, observations=["source", "check"])
    weak = evaluator.evaluate(goal="research", result="answer", verified=False)
    assert good.score > weak.score
    assert "verification" not in good.improvement_targets


def test_empty_result_is_improvement_target():
    result = SelfEvaluator().evaluate(goal="research", result="", verified=False)
    assert result.score < 1.0
    assert "result_completeness" in result.improvement_targets


def test_evaluation_is_bounded_and_non_authoritative():
    result = SelfEvaluator(max_chars=100).evaluate(goal="x" * 500, result="answer", verified=True, observations=["x"] * 20)
    assert len(result.context) <= 100
    assert "not instructions or authority" in result.context


def test_invalid_bounds_rejected():
    try:
        SelfEvaluator(max_findings=0)
        assert False
    except ValueError:
        pass

import pytest

from app.evaluation_lab import BoundedEvaluationLab, EvaluationError


def test_evaluation_scores_exact_matches():
    report = BoundedEvaluationLab().evaluate([
        ("a", "yes", "yes"),
        ("b", "yes", "no"),
    ])
    assert report.score == 50
    assert report.passed == 1
    assert report.failed == 1


def test_empty_evaluation_is_deterministic():
    report = BoundedEvaluationLab().evaluate([])
    assert report.score == 0
    assert report.cases == ()


def test_case_budget_is_enforced():
    lab = BoundedEvaluationLab(max_cases=1)
    with pytest.raises(EvaluationError):
        lab.evaluate([("a", "x", "x"), ("b", "x", "x")])


def test_comparison_is_candidate_minus_baseline():
    lab = BoundedEvaluationLab()
    baseline = lab.evaluate([("a", "x", "x")])
    candidate = lab.evaluate([("a", "x", "x"), ("b", "x", "no")])
    assert lab.compare(baseline, candidate) == -50

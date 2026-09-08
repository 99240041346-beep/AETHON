import pytest

from app.evaluation_lab import BoundedEvaluationLab, EvaluationError


def test_required_case_fields_are_validated():
    lab = BoundedEvaluationLab()
    with pytest.raises(EvaluationError):
        lab.evaluate([("", "expected", "actual")])
    with pytest.raises(EvaluationError):
        lab.evaluate([("id", "", "actual")])

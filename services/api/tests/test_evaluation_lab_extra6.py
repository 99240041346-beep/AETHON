import pytest
from app.evaluation_lab import BoundedEvaluationLab, EvaluationError

def test_required_fields_are_hard():
    lab = BoundedEvaluationLab()
    with pytest.raises(EvaluationError):
        lab.evaluate([('', 'x', 'x')])
    with pytest.raises(EvaluationError):
        lab.evaluate([('a', '', 'x')])

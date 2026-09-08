import pytest
from app.evaluation_lab import BoundedEvaluationLab, EvaluationError

def test_case_budget_is_hard():
    with pytest.raises(EvaluationError):
        BoundedEvaluationLab(max_cases=1).evaluate([('a','x','x'),('b','x','x')])

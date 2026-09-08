from app.evaluation_lab import BoundedEvaluationLab

def test_exact_matching_is_deterministic():
    lab = BoundedEvaluationLab()
    assert lab.evaluate([('a',' hello ','hello')]).cases[0].passed is True

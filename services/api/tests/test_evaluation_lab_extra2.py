from app.evaluation_lab import BoundedEvaluationLab

def test_comparison_is_deterministic():
    lab = BoundedEvaluationLab()
    baseline = lab.evaluate([('a', 'x', 'x')])
    candidate = lab.evaluate([('a', 'x', 'no')])
    assert lab.compare(baseline, candidate) == -100

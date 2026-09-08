from app.evaluation_lab import BoundedEvaluationLab

def test_baseline_delta():
    lab = BoundedEvaluationLab()
    baseline = lab.evaluate([('a','x','x')])
    candidate = lab.evaluate([('a','x','x')])
    assert lab.compare(baseline, candidate) == 0

from app.evaluation_lab import BoundedEvaluationLab

def test_comparison_direction():
    lab = BoundedEvaluationLab()
    low = lab.evaluate([('a','x','no')])
    high = lab.evaluate([('a','x','x')])
    assert lab.compare(low, high) == 100

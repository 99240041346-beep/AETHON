from app.evaluation_lab import BoundedEvaluationLab

def test_failed_count():
    report = BoundedEvaluationLab().evaluate([('a','x','no')])
    assert report.failed == 1 and report.score == 0

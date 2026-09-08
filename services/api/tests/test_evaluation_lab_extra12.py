from app.evaluation_lab import BoundedEvaluationLab

def test_passed_count():
    report = BoundedEvaluationLab().evaluate([('a','x','x')])
    assert report.passed == 1

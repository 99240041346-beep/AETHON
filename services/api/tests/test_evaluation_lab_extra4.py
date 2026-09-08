from app.evaluation_lab import BoundedEvaluationLab

def test_empty_report_is_zero_score():
    report = BoundedEvaluationLab().evaluate([])
    assert report.score == 0 and report.passed == 0 and report.failed == 0

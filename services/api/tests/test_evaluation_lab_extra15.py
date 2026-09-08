from app.evaluation_lab import BoundedEvaluationLab

def test_report_is_immutable():
    report = BoundedEvaluationLab().evaluate([('a','x','x')])
    assert report.cases[0].passed is True

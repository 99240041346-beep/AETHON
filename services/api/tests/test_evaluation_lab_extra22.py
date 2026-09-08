from app.evaluation_lab import BoundedEvaluationLab

def test_report_contains_cases():
    report = BoundedEvaluationLab().evaluate([('id','expected','expected')])
    assert len(report.cases) == 1

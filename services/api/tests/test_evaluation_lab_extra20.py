from app.evaluation_lab import BoundedEvaluationLab

def test_report_counts_sum_to_cases():
    report = BoundedEvaluationLab().evaluate([('a','x','x'),('b','x','no')])
    assert report.passed + report.failed == len(report.cases)

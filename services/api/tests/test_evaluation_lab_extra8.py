from app.evaluation_lab import BoundedEvaluationLab

def test_output_records_include_case_identity():
    report = BoundedEvaluationLab().evaluate([('case-1','x','x')])
    assert report.cases[0].case_id == 'case-1'
    assert report.cases[0].score == 100

from app.evaluation_lab import BoundedEvaluationLab

def test_bounded_case_text():
    report = BoundedEvaluationLab(max_text=4).evaluate([('a','  test  ','test')])
    assert report.cases[0].expected == 'test'

from app.evaluation_lab import BoundedEvaluationLab

def test_text_is_trimmed_to_configured_bound():
    report = BoundedEvaluationLab(max_text=3).evaluate([('a', 'abcd', 'abc')])
    assert report.cases[0].expected == 'abc'
    assert report.cases[0].actual == 'abc'
    assert report.score == 100

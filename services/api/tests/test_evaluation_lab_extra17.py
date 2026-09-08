from app.evaluation_lab import BoundedEvaluationLab

def test_reports_are_independent():
    lab = BoundedEvaluationLab()
    first = lab.evaluate([('a','x','x')])
    second = lab.evaluate([('b','x','no')])
    assert first.score == 100 and second.score == 0

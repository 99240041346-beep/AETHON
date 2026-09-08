from app.evaluation_lab import BoundedEvaluationLab

def test_score_range():
    report = BoundedEvaluationLab().evaluate([('a','x','x')])
    assert 0 <= report.score <= 100

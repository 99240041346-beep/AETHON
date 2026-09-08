from app.evaluation_lab import BoundedEvaluationLab

def test_score_rounding():
    report = BoundedEvaluationLab().evaluate([('a','x','x'),('b','x','x'),('c','x','no')])
    assert report.score == 67

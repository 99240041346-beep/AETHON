from app.evaluation_lab import BoundedEvaluationLab

def test_actual_text_is_normalized():
    report = BoundedEvaluationLab().evaluate([('a','yes','  yes  ')])
    assert report.score == 100

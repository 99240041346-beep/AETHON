from app.evaluation_lab import BoundedEvaluationLab

def test_case_order_is_preserved():
    report = BoundedEvaluationLab().evaluate([('b','x','x'),('a','x','x')])
    assert [c.case_id for c in report.cases] == ['b','a']

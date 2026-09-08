from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_full_ties_are_order_independent():
    request = ModelRequest("task")
    a = ModelRouter([ModelCandidate("z"), ModelCandidate("a")]).route(request)
    b = ModelRouter([ModelCandidate("a"), ModelCandidate("z")]).route(request)
    assert a == b

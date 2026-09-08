from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_zero_priority_is_valid():
    assert ModelRouter([ModelCandidate("x", priority=0)]).route(ModelRequest("x")).model == "x"

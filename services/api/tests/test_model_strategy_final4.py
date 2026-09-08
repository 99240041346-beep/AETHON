from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_route_reason_is_present():
    assert ModelRouter([ModelCandidate("x")]).route(ModelRequest("x")).reason == "deterministic policy selection"

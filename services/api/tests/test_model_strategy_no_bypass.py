from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_route_is_metadata_only():
    route = ModelRouter([ModelCandidate("x")]).route(ModelRequest("task"))
    assert route.model == "x"
    assert route.reason == "deterministic policy selection"

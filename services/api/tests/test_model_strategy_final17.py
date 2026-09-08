from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_empty_capability_request_allows_any_candidate():
    assert ModelRouter([ModelCandidate("x")]).route(ModelRequest("task")).model == "x"

from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_route_contains_policy_metadata():
    route = ModelRouter([ModelCandidate("safe", ("text",), priority=10)]).route(ModelRequest("answer", ("text",)))
    assert route.model == "safe"
    assert route.reason
    assert route.requires_approval is False

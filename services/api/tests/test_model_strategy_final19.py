from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_route_metadata_has_no_provider_secret():
    route = ModelRouter([ModelCandidate("model")]).route(ModelRequest("task"))
    assert "key" not in route.reason.lower()
    assert "token" not in route.reason.lower()

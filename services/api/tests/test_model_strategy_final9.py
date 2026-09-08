from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_router_returns_route_without_execution():
    route = ModelRouter([ModelCandidate("provider-model")]).route(ModelRequest("task"))
    assert route.model == "provider-model"

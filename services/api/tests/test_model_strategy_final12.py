from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_route_under_exact_limits_is_allowed():
    route = ModelRouter([ModelCandidate("bounded", cost=4, latency_ms=400)]).route(ModelRequest("task", max_cost=4, max_latency_ms=400))
    assert route.model == "bounded"

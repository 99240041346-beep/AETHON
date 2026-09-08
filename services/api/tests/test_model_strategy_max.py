from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_exact_cost_and_latency_limits_are_inclusive():
    router = ModelRouter([ModelCandidate("bounded", cost=2, latency_ms=200)])
    assert router.route(ModelRequest("x", max_cost=2, max_latency_ms=200)).model == "bounded"

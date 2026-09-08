from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_latency_breaks_cost_ties():
    router = ModelRouter([
        ModelCandidate("slow", cost=1, latency_ms=200),
        ModelCandidate("fast", cost=1, latency_ms=100),
    ])
    assert router.route(ModelRequest("x")).model == "fast"

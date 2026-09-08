from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_latency_constraint_filters_slow_models():
    router = ModelRouter([
        ModelCandidate("slow", ("text",), priority=100, latency_ms=500),
        ModelCandidate("fast", ("text",), priority=50, latency_ms=100),
    ])
    assert router.route(ModelRequest("x", ("text",), max_latency_ms=100)).model == "fast"

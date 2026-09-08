from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_ties_break_by_name_deterministically():
    router = ModelRouter([
        ModelCandidate("zeta", ("text",), priority=50, cost=1, latency_ms=10),
        ModelCandidate("alpha", ("text",), priority=50, cost=1, latency_ms=10),
    ])
    assert router.route(ModelRequest("x", ("text",))).model == "alpha"

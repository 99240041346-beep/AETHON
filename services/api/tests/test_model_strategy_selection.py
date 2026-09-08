from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_combined_constraints_select_only_matching_candidate():
    router = ModelRouter([
        ModelCandidate("wide", ("text",), priority=100, cost=5, latency_ms=500),
        ModelCandidate("balanced", ("text",), priority=80, cost=2, latency_ms=200),
    ])
    route = router.route(ModelRequest("x", ("text",), max_cost=2, max_latency_ms=200))
    assert route.model == "balanced"

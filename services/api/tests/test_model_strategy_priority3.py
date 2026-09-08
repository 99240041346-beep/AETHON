from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_cost_breaks_priority_ties():
    router = ModelRouter([
        ModelCandidate("costly", priority=10, cost=2),
        ModelCandidate("cheap", priority=10, cost=1),
    ])
    assert router.route(ModelRequest("x")).model == "cheap"

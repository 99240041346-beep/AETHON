from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_priority_precedes_cost():
    router = ModelRouter([
        ModelCandidate("cheap", ("text",), priority=20, cost=1),
        ModelCandidate("preferred", ("text",), priority=30, cost=9),
    ])
    assert router.route(ModelRequest("x", ("text",))).model == "preferred"

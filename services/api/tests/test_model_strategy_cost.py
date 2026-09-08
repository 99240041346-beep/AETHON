from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_cost_constraint_filters_expensive_models():
    router = ModelRouter([
        ModelCandidate("expensive", ("text",), priority=100, cost=5),
        ModelCandidate("cheap", ("text",), priority=50, cost=2),
    ])
    assert router.route(ModelRequest("x", ("text",), max_cost=2)).model == "cheap"

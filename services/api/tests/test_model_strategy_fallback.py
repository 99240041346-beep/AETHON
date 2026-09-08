from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_lower_priority_candidate_is_used_when_best_is_constrained():
    router = ModelRouter([
        ModelCandidate("premium", ("text",), priority=100, cost=10),
        ModelCandidate("economy", ("text",), priority=50, cost=1),
    ])
    assert router.route(ModelRequest("x", ("text",), max_cost=1)).model == "economy"

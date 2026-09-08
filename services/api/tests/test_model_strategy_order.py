from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_higher_priority_wins_when_constraints_match():
    router = ModelRouter([
        ModelCandidate("low", ("text",), priority=10),
        ModelCandidate("high", ("text",), priority=20),
    ])
    assert router.route(ModelRequest("x", ("text",))).model == "high"

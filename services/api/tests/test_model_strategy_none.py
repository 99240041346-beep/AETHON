from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_optional_constraints_are_unbounded_when_absent():
    router = ModelRouter([ModelCandidate("x", ("text",), priority=1, cost=99, latency_ms=999)])
    assert router.route(ModelRequest("x", ("text",))).model == "x"

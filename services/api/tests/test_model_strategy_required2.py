from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_all_required_capabilities_must_match():
    router = ModelRouter([ModelCandidate("multi", ("text", "vision"))])
    assert router.route(ModelRequest("x", ("text", "vision"))).model == "multi"

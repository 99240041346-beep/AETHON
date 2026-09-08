from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_blank_capabilities_are_ignored():
    router = ModelRouter([ModelCandidate("x", ("", "text", " "))])
    assert router.route(ModelRequest("x", ("text",))).model == "x"

from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_exact_capability_route():
    assert ModelRouter([ModelCandidate("text", ("text",))]).route(ModelRequest("task", ("text",))).model == "text"

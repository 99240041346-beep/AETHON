from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_candidate_with_extra_capability_remains_eligible():
    router = ModelRouter([ModelCandidate("vision-text", ("text", "vision"))])
    assert router.route(ModelRequest("x", ("text",))).model == "vision-text"

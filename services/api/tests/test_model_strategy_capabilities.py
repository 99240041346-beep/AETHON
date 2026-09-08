from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_capability_matching_is_case_insensitive():
    router = ModelRouter([ModelCandidate("vision", (" Vision ",))])
    assert router.route(ModelRequest("image", ("VISION",))).model == "vision"

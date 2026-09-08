from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_approval_candidate_is_excluded_without_approval():
    router = ModelRouter([ModelCandidate("guarded", ("text",), priority=100, requires_approval=True), ModelCandidate("open", ("text",), priority=1)])
    assert router.route(ModelRequest("x", ("text",))).model == "open"

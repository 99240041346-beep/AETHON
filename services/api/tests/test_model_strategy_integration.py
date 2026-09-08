from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_approval_candidate_is_skipped_without_approval():
    router = ModelRouter([
        ModelCandidate("approved", ("text",), priority=100, requires_approval=True),
        ModelCandidate("safe", ("text",), priority=90),
    ])
    assert router.route(ModelRequest("answer", ("text",))).model == "safe"

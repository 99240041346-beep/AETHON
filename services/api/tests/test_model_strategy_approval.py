from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_approved_candidate_route_marks_approval_metadata():
    route = ModelRouter([ModelCandidate("guarded", ("text",), requires_approval=True)]).route(ModelRequest("x", ("text",)), approve=True)
    assert route.model == "guarded"
    assert route.requires_approval is True

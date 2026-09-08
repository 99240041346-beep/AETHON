from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_approval_flag_is_preserved_on_selected_candidate():
    route = ModelRouter([ModelCandidate("guarded", requires_approval=True)]).route(ModelRequest("x"), approve=True)
    assert route.requires_approval is True

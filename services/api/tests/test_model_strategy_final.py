from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_final_route_contract_is_stable():
    route = ModelRouter([ModelCandidate("model", ("text",), priority=42)]).route(ModelRequest("hello", ("text",)))
    assert (route.model, route.requires_approval) == ("model", False)

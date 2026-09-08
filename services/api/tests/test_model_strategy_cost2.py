from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_zero_cost_candidate_is_valid():
    assert ModelRouter([ModelCandidate("free", cost=0)]).route(ModelRequest("x")).model == "free"

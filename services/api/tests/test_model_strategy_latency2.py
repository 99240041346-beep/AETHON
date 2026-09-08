from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_zero_latency_candidate_is_valid():
    assert ModelRouter([ModelCandidate("instant", latency_ms=0)]).route(ModelRequest("x")).model == "instant"

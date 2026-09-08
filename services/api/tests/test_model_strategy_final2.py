from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_same_inputs_produce_same_route():
    router = ModelRouter([ModelCandidate("b", priority=5), ModelCandidate("a", priority=5)])
    request = ModelRequest("task")
    assert router.route(request) == router.route(request)

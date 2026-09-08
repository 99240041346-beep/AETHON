from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_task_whitespace_is_accepted_after_normalization():
    route = ModelRouter([ModelCandidate("x")]).route(ModelRequest("  task  "))
    assert route.model == "x"

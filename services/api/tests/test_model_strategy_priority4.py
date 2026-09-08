from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_name_breaks_full_tie():
    router = ModelRouter([ModelCandidate("z"), ModelCandidate("a")])
    assert router.route(ModelRequest("x")).model == "a"

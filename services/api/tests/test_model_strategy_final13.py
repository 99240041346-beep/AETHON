from app.model_strategy import ModelCandidate, ModelRouter


def test_normalized_capabilities_are_tuple():
    assert isinstance(ModelRouter([ModelCandidate("x", ("text",))]).candidates[0].capabilities, tuple)

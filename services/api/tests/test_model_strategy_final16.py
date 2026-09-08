from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter


def test_selected_model_identity_is_exact():
    assert ModelRouter([ModelCandidate("AETHON-model")]).route(ModelRequest("task")).model == "AETHON-model"

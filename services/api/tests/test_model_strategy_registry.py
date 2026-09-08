from app.model_strategy import ModelCandidate, ModelRouter


def test_candidate_metadata_is_normalized():
    candidate = ModelCandidate(" model ", (" Text ", "text", " vision "))
    normalized = ModelRouter([candidate]).candidates[0]
    assert normalized.name == "model"
    assert normalized.capabilities == ("text", "vision")

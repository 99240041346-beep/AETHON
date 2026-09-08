from app.model_strategy import ModelCandidate, ModelRouter


def test_candidate_collection_is_immutable_tuple():
    router = ModelRouter([ModelCandidate("x")])
    assert isinstance(router.candidates, tuple)

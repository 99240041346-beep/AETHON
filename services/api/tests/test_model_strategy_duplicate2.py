import pytest
from app.model_strategy import ModelCandidate, ModelRouter, ModelRoutingError


def test_duplicate_candidate_names_are_rejected_after_trim():
    with pytest.raises(ModelRoutingError, match="duplicate"):
        ModelRouter([ModelCandidate("x"), ModelCandidate(" x ")])

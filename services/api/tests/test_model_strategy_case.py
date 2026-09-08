import pytest
from app.model_strategy import ModelCandidate, ModelRouter, ModelRoutingError


def test_duplicate_names_ignore_case():
    with pytest.raises(ModelRoutingError, match="duplicate"):
        ModelRouter([ModelCandidate("Model"), ModelCandidate("model")])

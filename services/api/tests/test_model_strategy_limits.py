import pytest
from app.model_strategy import ModelCandidate, ModelRouter, ModelRoutingError


def test_model_name_bound_is_enforced():
    with pytest.raises(ModelRoutingError, match="invalid model name"):
        ModelRouter([ModelCandidate("x" * 5)], max_name=4)

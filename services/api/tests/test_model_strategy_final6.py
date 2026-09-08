import pytest
from app.model_strategy import ModelCandidate, ModelRouter, ModelRoutingError


def test_negative_priority_is_rejected():
    with pytest.raises(ModelRoutingError, match="invalid model candidate limits"):
        ModelRouter([ModelCandidate("x", priority=-1)])

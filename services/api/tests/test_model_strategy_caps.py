import pytest
from app.model_strategy import ModelCandidate, ModelRouter, ModelRoutingError


def test_negative_candidate_cost_is_rejected():
    with pytest.raises(ModelRoutingError, match="invalid model candidate limits"):
        ModelRouter([ModelCandidate("x", cost=-1)])


def test_negative_candidate_latency_is_rejected():
    with pytest.raises(ModelRoutingError, match="invalid model candidate limits"):
        ModelRouter([ModelCandidate("x", latency_ms=-1)])

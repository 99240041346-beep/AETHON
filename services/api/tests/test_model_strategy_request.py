import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_negative_latency_request_is_rejected():
    with pytest.raises(ModelRoutingError, match="non-negative"):
        ModelRouter([ModelCandidate("x")]).route(ModelRequest("x", max_latency_ms=-1))

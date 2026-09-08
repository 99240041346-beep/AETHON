import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_routing_failure_is_explicit():
    with pytest.raises(ModelRoutingError):
        ModelRouter([ModelCandidate("text", ("text",))]).route(ModelRequest("x", ("audio",)))

import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_approval_request_never_silently_downgrades():
    with pytest.raises(ModelRoutingError, match="approval required"):
        ModelRouter([ModelCandidate("x")]).route(ModelRequest("sensitive", requires_approval=True))

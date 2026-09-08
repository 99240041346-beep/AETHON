import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_request_approval_blocks_before_selection():
    with pytest.raises(ModelRoutingError, match="approval required"):
        ModelRouter([ModelCandidate("x")]).route(ModelRequest("x", requires_approval=True))

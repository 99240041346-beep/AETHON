import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_empty_task_is_rejected():
    with pytest.raises(ModelRoutingError, match="task is required"):
        ModelRouter([ModelCandidate("x")]).route(ModelRequest(" "))

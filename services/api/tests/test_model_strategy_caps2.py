import pytest
from app.model_strategy import ModelRequest, ModelRouter, ModelRoutingError


def test_empty_registry_has_no_eligible_model():
    with pytest.raises(ModelRoutingError, match="no eligible"):
        ModelRouter([]).route(ModelRequest("x"))

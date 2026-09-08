import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_missing_required_capability_rejects_route():
    router = ModelRouter([ModelCandidate("text", ("text",))])
    with pytest.raises(ModelRoutingError, match="no eligible"):
        router.route(ModelRequest("audio task", ("audio",)))

import pytest

from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_selects_highest_priority_eligible_model():
    router = ModelRouter([
        ModelCandidate("fast", ("text",), priority=70, cost=1, latency_ms=100),
        ModelCandidate("quality", ("text",), priority=90, cost=3, latency_ms=500),
    ])
    assert router.route(ModelRequest("answer", ("text",))).model == "quality"


def test_constraints_produce_deterministic_fallback():
    router = ModelRouter([
        ModelCandidate("premium", ("text",), priority=100, cost=10, latency_ms=500),
        ModelCandidate("economy", ("text",), priority=50, cost=1, latency_ms=100),
    ])
    assert router.route(ModelRequest("answer", ("text",), max_cost=1, max_latency_ms=100)).model == "economy"


def test_approval_gates_request_and_candidate():
    guarded = ModelRouter([ModelCandidate("guarded", ("text",), requires_approval=True)])
    with pytest.raises(ModelRoutingError, match="no eligible"):
        guarded.route(ModelRequest("x", ("text",)))
    with pytest.raises(ModelRoutingError, match="approval required"):
        guarded.route(ModelRequest("x", ("text",), requires_approval=True))
    assert guarded.route(ModelRequest("x", ("text",)), approve=True).requires_approval is True


def test_duplicate_and_invalid_candidates_are_rejected():
    with pytest.raises(ModelRoutingError, match="duplicate"):
        ModelRouter([ModelCandidate("A"), ModelCandidate(" a ")])
    with pytest.raises(ModelRoutingError, match="limits"):
        ModelRouter([ModelCandidate("x", cost=-1)])


def test_capabilities_are_case_insensitive_and_empty_registry_fails():
    router = ModelRouter([ModelCandidate("vision", (" Vision ",))])
    assert router.route(ModelRequest("image", ("VISION",))).model == "vision"
    with pytest.raises(ModelRoutingError, match="no eligible"):
        ModelRouter([]).route(ModelRequest("x"))

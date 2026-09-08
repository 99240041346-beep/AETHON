import pytest

from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def candidates():
    return [
        ModelCandidate("fast", ("text",), priority=70, cost=1.0, latency_ms=100),
        ModelCandidate("quality", ("text", "vision"), priority=90, cost=3.0, latency_ms=500),
        ModelCandidate("approval", ("text",), priority=100, cost=2.0, latency_ms=200, requires_approval=True),
    ]


def test_route_is_deterministic_by_priority_then_cost_then_latency():
    route = ModelRouter(candidates()).route(ModelRequest("answer", ("text",)), approve=True)
    assert route.model == "approval"


def test_capability_and_budget_constraints_filter_candidates():
    route = ModelRouter(candidates()).route(ModelRequest("see", ("vision",), max_cost=3, max_latency_ms=500))
    assert route.model == "quality"


def test_approval_is_required_for_approval_request():
    with pytest.raises(ModelRoutingError, match="approval required"):
        ModelRouter(candidates()).route(ModelRequest("answer", ("text",), requires_approval=True))


def test_duplicate_candidates_are_rejected():
    with pytest.raises(ModelRoutingError, match="duplicate"):
        ModelRouter([ModelCandidate("A"), ModelCandidate("a")])


def test_no_eligible_candidate_is_rejected():
    with pytest.raises(ModelRoutingError, match="no eligible"):
        ModelRouter(candidates()).route(ModelRequest("x", ("audio",)))

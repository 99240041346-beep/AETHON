import pytest
from app.model_strategy import ModelCandidate, ModelRequest, ModelRouter, ModelRoutingError


def test_candidate_budget_is_enforced():
    with pytest.raises(ModelRoutingError, match="budget"):
        ModelRouter([ModelCandidate(str(i)) for i in range(3)], max_candidates=2)


def test_negative_request_limits_are_rejected():
    router = ModelRouter([ModelCandidate("x")])
    with pytest.raises(ModelRoutingError, match="non-negative"):
        router.route(ModelRequest("x", max_cost=-1))

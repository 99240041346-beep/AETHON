import pytest

from app.distributed_execution import (
    DistributedCandidate,
    DistributedRequest,
    DistributedRouter,
    DistributedRoutingError,
)


def test_selects_deterministically_by_priority_then_load():
    router = DistributedRouter([
        DistributedCandidate("node-b", region="eu", priority=80, load=50),
        DistributedCandidate("node-a", region="us", priority=80, load=10),
    ])
    assert router.route(DistributedRequest("run")).candidate == "node-a"


def test_capability_region_and_resource_constraints_are_hard_filters():
    router = DistributedRouter([
        DistributedCandidate("premium", ("gpu",), region="us", cost=10, latency_ms=500, priority=100),
        DistributedCandidate("edge", ("gpu",), region="eu", cost=2, latency_ms=100, priority=50),
    ])
    request = DistributedRequest("infer", ("GPU",), preferred_region="EU", max_cost=2, max_latency_ms=100)
    assert router.route(request).candidate == "edge"


def test_approval_gates_request_and_guarded_candidate():
    guarded = DistributedRouter([DistributedCandidate("secure", requires_approval=True)])
    with pytest.raises(DistributedRoutingError, match="no eligible"):
        guarded.route(DistributedRequest("run"))
    with pytest.raises(DistributedRoutingError, match="approval required"):
        guarded.route(DistributedRequest("run", requires_approval=True))
    assert guarded.route(DistributedRequest("run"), approve=True).candidate == "secure"


def test_invalid_candidates_and_empty_registry_fail_closed():
    with pytest.raises(DistributedRoutingError, match="duplicate"):
        DistributedRouter([DistributedCandidate("A"), DistributedCandidate(" a ")])
    with pytest.raises(DistributedRoutingError, match="limits"):
        DistributedRouter([DistributedCandidate("node", load=101)])
    with pytest.raises(DistributedRoutingError, match="no eligible"):
        DistributedRouter([]).route(DistributedRequest("run"))

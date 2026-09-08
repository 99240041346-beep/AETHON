import pytest

from app.hybrid_execution import ExecutionCandidate, ExecutionLocation, HybridRequest, HybridRouter, HybridRoutingError


def test_auto_selects_deterministically_across_local_and_cloud():
    router = HybridRouter([
        ExecutionCandidate("cloud", ExecutionLocation.CLOUD, cost=2, latency_ms=300, priority=80),
        ExecutionCandidate("local", ExecutionLocation.LOCAL, cost=0, latency_ms=100, priority=80),
    ])
    route = router.route(HybridRequest("run"))
    assert route.candidate == "local"
    assert route.location is ExecutionLocation.LOCAL


def test_explicit_location_is_hard_constraint():
    router = HybridRouter([
        ExecutionCandidate("local", ExecutionLocation.LOCAL, priority=100),
        ExecutionCandidate("cloud", ExecutionLocation.CLOUD, priority=50),
    ])
    assert router.route(HybridRequest("run", ExecutionLocation.CLOUD)).candidate == "cloud"


def test_network_requires_explicit_approval_and_network_capability():
    router = HybridRouter([
        ExecutionCandidate("offline", ExecutionLocation.LOCAL, network=False),
        ExecutionCandidate("networked", ExecutionLocation.CLOUD, network=True, requires_approval=True),
    ])
    with pytest.raises(HybridRoutingError, match="network approval"):
        router.route(HybridRequest("run", requires_network=True))
    with pytest.raises(HybridRoutingError, match="no eligible"):
        router.route(HybridRequest("run"), approve_network=False)
    assert router.route(HybridRequest("run", requires_network=True), approve_network=True).candidate == "networked"


def test_cost_and_latency_constraints_limit_fallback():
    router = HybridRouter([
        ExecutionCandidate("expensive", ExecutionLocation.CLOUD, cost=10, latency_ms=500, priority=100),
        ExecutionCandidate("cheap", ExecutionLocation.LOCAL, cost=1, latency_ms=100, priority=50),
    ])
    assert router.route(HybridRequest("run", max_cost=1, max_latency_ms=100)).candidate == "cheap"


def test_invalid_candidates_and_empty_task_are_rejected():
    with pytest.raises(HybridRoutingError, match="duplicate"):
        HybridRouter([ExecutionCandidate("A", ExecutionLocation.LOCAL), ExecutionCandidate(" a ", ExecutionLocation.LOCAL)])
    with pytest.raises(HybridRoutingError, match="location"):
        HybridRouter([ExecutionCandidate("auto", ExecutionLocation.AUTO)])
    with pytest.raises(HybridRoutingError, match="task"):
        HybridRouter([ExecutionCandidate("local", ExecutionLocation.LOCAL)]).route(HybridRequest("  "))

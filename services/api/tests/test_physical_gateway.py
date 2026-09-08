import pytest

from app.physical_gateway import (
    PhysicalCandidate,
    PhysicalGateway,
    PhysicalGatewayError,
    PhysicalOperation,
    PhysicalRequest,
)


def test_selects_highest_priority_supported_adapter():
    gateway = PhysicalGateway([
        PhysicalCandidate("lamp", (PhysicalOperation.READ, PhysicalOperation.ACTUATE), priority=40),
        PhysicalCandidate("controller", (PhysicalOperation.ACTUATE,), priority=80),
    ])
    route = gateway.route(PhysicalRequest(PhysicalOperation.ACTUATE, "relay-1"))
    assert route.candidate == "controller"


def test_marked_operation_requires_explicit_approval():
    gateway = PhysicalGateway([PhysicalCandidate("motor", (PhysicalOperation.ACTUATE,), requires_approval=True)])
    with pytest.raises(PhysicalGatewayError, match="approval required"):
        gateway.route(PhysicalRequest(PhysicalOperation.ACTUATE, "motor-1", requires_approval=True))
    assert gateway.route(PhysicalRequest(PhysicalOperation.ACTUATE, "motor-1", requires_approval=True), approve=True).candidate == "motor"


def test_guarded_candidate_is_not_eligible_without_approval():
    gateway = PhysicalGateway([PhysicalCandidate("door", (PhysicalOperation.WRITE,), requires_approval=True)])
    with pytest.raises(PhysicalGatewayError, match="no eligible"):
        gateway.route(PhysicalRequest(PhysicalOperation.WRITE, "door-1"))


def test_missing_adapter_invalid_input_and_payload_budget_fail_closed():
    gateway = PhysicalGateway([PhysicalCandidate("sensor", (PhysicalOperation.READ,))], max_payload=4)
    with pytest.raises(PhysicalGatewayError, match="no eligible"):
        gateway.route(PhysicalRequest(PhysicalOperation.ACTUATE, "sensor-1"))
    with pytest.raises(PhysicalGatewayError, match="target"):
        gateway.route(PhysicalRequest(PhysicalOperation.READ, ""))
    with pytest.raises(PhysicalGatewayError, match="payload"):
        gateway.route(PhysicalRequest(PhysicalOperation.READ, "sensor-1", "12345"))


def test_duplicate_candidates_and_invalid_priority_are_rejected():
    with pytest.raises(PhysicalGatewayError, match="duplicate"):
        PhysicalGateway([PhysicalCandidate("A", (PhysicalOperation.READ,)), PhysicalCandidate(" a ", (PhysicalOperation.READ,))])
    with pytest.raises(PhysicalGatewayError, match="priority"):
        PhysicalGateway([PhysicalCandidate("sensor", (PhysicalOperation.READ,), priority=101)])

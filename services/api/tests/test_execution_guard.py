import pytest

from aethon.execution_guard import ExecutionGuard, ExecutionGuardError
from aethon.schemas import RiskClass


def test_low_risk_execution_is_allowed():
    decision = ExecutionGuard().evaluate(RiskClass.LOW)
    assert decision.decision == "ALLOW"


def test_side_effects_require_explicit_approval():
    guard = ExecutionGuard()
    with pytest.raises(ExecutionGuardError, match="explicit execution approval"):
        guard.evaluate(RiskClass.LOW, side_effects=True)
    decision = guard.evaluate(RiskClass.LOW, side_effects=True, approved=True)
    assert decision.decision == "ALLOW"
    assert decision.approved is True


def test_medium_and_high_risk_fail_closed_without_approval():
    guard = ExecutionGuard()
    for risk in (RiskClass.MEDIUM, RiskClass.HIGH):
        with pytest.raises(ExecutionGuardError, match="explicit execution approval"):
            guard.evaluate(risk)
        assert guard.evaluate(risk, approved=True).decision == "ALLOW"


def test_critical_risk_can_never_be_approved():
    with pytest.raises(ExecutionGuardError, match="denied"):
        ExecutionGuard().evaluate(RiskClass.CRITICAL, approved=True)

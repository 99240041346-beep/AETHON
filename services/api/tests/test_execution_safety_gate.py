import pytest

from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.schemas import RiskClass


def test_low_risk_is_allowed_without_approval():
    result = SafetyExecutionGate().authorize(RiskClass.LOW)
    assert result.policy_decision == "ALLOW"
    assert result.effective_decision == "ALLOW"
    assert result.approved is False


def test_side_effects_require_explicit_approval():
    gate = SafetyExecutionGate()
    with pytest.raises(ExecutionAuthorizationError, match="explicit execution approval"):
        gate.authorize(RiskClass.LOW, side_effects=True)
    result = gate.authorize(RiskClass.LOW, side_effects=True, approved=True)
    assert result.policy_decision == "APPROVAL_REQUIRED"
    assert result.effective_decision == "ALLOW"


def test_medium_and_high_require_approval():
    gate = SafetyExecutionGate()
    for risk in (RiskClass.MEDIUM, RiskClass.HIGH):
        with pytest.raises(ExecutionAuthorizationError, match="explicit execution approval"):
            gate.authorize(risk)
        assert gate.authorize(risk, approved=True).effective_decision == "ALLOW"


def test_critical_is_denied_even_with_approval():
    with pytest.raises(ExecutionAuthorizationError, match="denied"):
        SafetyExecutionGate().authorize(RiskClass.CRITICAL, approved=True)

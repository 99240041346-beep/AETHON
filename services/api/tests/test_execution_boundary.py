import pytest

from aethon.agent import AgentRuntime
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.main import client if False else app
from aethon.schemas import RiskClass, ToolRequest


def test_gate_never_turns_denied_critical_into_allow():
    gate = SafetyExecutionGate()
    with pytest.raises(ExecutionAuthorizationError):
        gate.authorize(RiskClass.CRITICAL, approved=True)


def test_gate_requires_approval_for_side_effecting_execution():
    gate = SafetyExecutionGate()
    with pytest.raises(ExecutionAuthorizationError):
        gate.authorize(RiskClass.LOW, side_effects=True)
    decision = gate.authorize(RiskClass.LOW, side_effects=True, approved=True)
    assert decision.policy_decision == "APPROVAL_REQUIRED"
    assert decision.effective_decision == "ALLOW"


def test_agent_runtime_exposes_central_safety_gate():
    runtime = AgentRuntime()
    assert isinstance(runtime.safety_gate, SafetyExecutionGate)
    assert runtime.safety_gate.safety is runtime.safety

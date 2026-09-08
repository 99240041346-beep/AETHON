import pytest
from fastapi.testclient import TestClient

from aethon.agent import AgentRuntime
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.main import app
from aethon.schemas import RiskClass


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


def test_http_tool_execution_fails_closed_when_gate_blocks(monkeypatch):
    class BlockingGate:
        def authorize(self, *args, **kwargs):
            raise ExecutionAuthorizationError("blocked by regression test")

    import app.main as main_module
    monkeypatch.setattr(main_module, "safety_gate", BlockingGate())
    response = TestClient(app).post(
        "/v1/tools/execute",
        json={"tool": "calculator", "arguments": {"expression": "2 + 2"}},
    )
    assert response.status_code == 403
    assert "blocked by regression test" in response.json()["detail"]

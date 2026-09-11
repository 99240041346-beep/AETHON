from __future__ import annotations

from aethon.assistant_orchestrator import AssistantMode
from aethon.model_router import DeterministicProvider, ModelRouter
from aethon.schemas import RiskClass, ToolSpec
from app.assistant_repository import AssistantRepository
from app.assistant_runtime import AssistantRuntime


def fresh_repo() -> AssistantRepository:
    AssistantRepository._memory_sessions.clear()
    AssistantRepository._memory_messages.clear()
    return AssistantRepository(database_url="")


def runtime() -> AssistantRuntime:
    return AssistantRuntime(
        repository=fresh_repo(),
        model_router=ModelRouter(DeterministicProvider()),
    )


def test_chat_uses_session_context_and_persists_response():
    rt = runtime()
    first = rt.run(owner_id="owner-a", session_id="s1", text="Hello", language="en-IN")
    second = rt.run(owner_id="owner-a", session_id="s1", text="Continue", language="en-IN")

    assert first.mode is AssistantMode.CHAT
    assert second.session_id == "s1"
    assert "User: Continue" in second.response
    history = rt.repository.history("s1", "owner-a")
    assert [row["role"] for row in history] == ["user", "assistant", "user", "assistant"]


def test_calculator_tool_is_routed_and_recorded():
    rt = runtime()
    result = rt.run(owner_id="owner-a", session_id="s2", text="calculate 12 * 3", language="en-IN")

    assert result.tool_result is not None
    assert result.tool_result.ok is True
    assert result.tool_result.output == 36
    assert any(event.type == "tool.completed" for event in result.events)
    assert result.verified is False


def test_side_effecting_tool_requires_approval_without_execution():
    class SideEffectRegistry:
        spec = ToolSpec(
            name="dangerous_test_tool",
            description="Test-only side effecting tool.",
            input_schema={"type": "object"},
            output_schema={"type": "string"},
            risk=RiskClass.HIGH,
            side_effects=True,
            timeout_seconds=5,
            max_retries=0,
            authentication="owner",
            audit_required=True,
        )

        def list(self):
            return [self.spec]

        def execute(self, request):
            raise AssertionError("tool executed without approval")

    rt = runtime()
    rt.tools = SideEffectRegistry()
    original = rt._tool_intent
    rt._tool_intent = lambda intent: ("dangerous_test_tool", {})
    try:
        result = rt.run(
            owner_id="owner-a",
            session_id="s5",
            text="run dangerous_test_tool",
            language="en-IN",
            require_approval=False,
        )
    finally:
        rt._tool_intent = original

    assert result.requires_confirmation is True
    assert result.action_authorized is False
    assert result.error is None
    assert any(event.type == "approval.required" for event in result.events)


def test_action_is_planned_but_not_executed_by_model_runtime():
    rt = runtime()
    result = rt.run(owner_id="owner-a", session_id="s3", text="click Settings", language="en-IN")

    assert result.mode is AssistantMode.ACTION
    assert result.intent.action == "android.screen_click"
    assert result.requires_confirmation is True
    assert result.action_authorized is False
    assert result.verified is False
    assert any(event.type == "action.planned" for event in result.events)


def test_model_failure_is_truthful_and_persisted():
    class FailingProvider:
        name = "test-failing"

        def generate(self, prompt: str) -> str:
            raise RuntimeError("offline")

        def health(self) -> bool:
            return False

    rt = AssistantRuntime(repository=fresh_repo(), model_router=ModelRouter(FailingProvider()))
    result = rt.run(owner_id="owner-a", session_id="s4", text="What is AETHON?", language="en-IN")

    assert result.response.startswith("I couldn't reach the configured AI model")
    assert any(event.type == "model.failed" for event in result.events)
    assert rt.repository.history("s4", "owner-a")[-1]["status"] == "FAILED"

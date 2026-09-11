from __future__ import annotations

from aethon.assistant_orchestrator import AssistantMode
from aethon.model_router import DeterministicProvider, ModelRouter
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

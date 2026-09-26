from app.assistant_orchestrator import AssistantOrchestrator


def test_plain_arithmetic_is_chat_tool_intent():
    orchestrator = AssistantOrchestrator()
    intent = orchestrator.classify("25 * 18")
    assert intent.mode.value == "CHAT"
    assert intent.text == "25 * 18"

from app.assistant_orchestrator import AssistantIntent, AssistantMode
from app.assistant_runtime import AssistantRuntime


def test_plain_arithmetic_routes_to_calculator():
    intent = AssistantIntent(AssistantMode.CHAT, "25 * 18")
    assert AssistantRuntime._tool_intent(intent) == ("calculator", {"expression": "25 * 18"})


def test_calculator_suffix_routes_to_calculator():
    intent = AssistantIntent(AssistantMode.CHAT, "25 * 18 → calculator")
    assert AssistantRuntime._tool_intent(intent) == ("calculator", {"expression": "25 * 18"})


def test_unicode_arithmetic_routes_to_calculator():
    intent = AssistantIntent(AssistantMode.CHAT, "25 × 18")
    assert AssistantRuntime._tool_intent(intent) == ("calculator", {"expression": "25 * 18"})

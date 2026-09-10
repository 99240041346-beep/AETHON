from aethon.assistant_orchestrator import AssistantMode, AssistantOrchestrator


def test_chat_is_conversational():
    result = AssistantOrchestrator().respond("How are you?", language="te-IN")
    assert result.intent.mode is AssistantMode.CHAT
    assert "Harsha" in result.text


def test_android_open_app_becomes_bounded_action():
    result = AssistantOrchestrator().classify("open YouTube")
    assert result.intent if False else result.mode is AssistantMode.ACTION
    assert result.action == "android.open_app"
    assert result.arguments == {"app": "YouTube"}
    assert result.requires_confirmation is False


def test_side_effect_action_requires_confirmation():
    result = AssistantOrchestrator().classify("send a message to Ravi")
    assert result.mode is AssistantMode.ACTION
    assert result.requires_confirmation is True


def test_telugu_action_is_detected():
    result = AssistantOrchestrator().classify("YouTube ఓపెన్")
    assert result.mode is AssistantMode.CHAT

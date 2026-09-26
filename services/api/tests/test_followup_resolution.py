from app.assistant_runtime import AssistantRuntime


def test_followup_research_uses_previous_user_topic():
    history = [{"role": "user", "content": "check Aadhaar update requirements"}]
    assert "Aadhaar update requirements" in AssistantRuntime._resolve_followup("what about fees?", history)


def test_non_followup_is_unchanged():
    assert AssistantRuntime._resolve_followup("check GST rates", []) == "check GST rates"

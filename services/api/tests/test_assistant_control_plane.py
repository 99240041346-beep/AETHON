from aethon.assistant_control_plane import AssistantMode, AssistantRequest, _detect_mode


def test_frontier_modes_are_bounded():
    assert {mode.value for mode in AssistantMode} == {
        "CHAT", "RESEARCH", "CODING", "BROWSER", "COMPUTER", "DOCUMENT", "DATA",
        "DEVICE", "WORKFLOW", "SCIENCE", "PHONE", "EMAIL", "SCHEDULING",
    }


def test_mode_detection_routes_common_intents():
    assert _detect_mode("debug my python code", []) is AssistantMode.CODING
    assert _detect_mode("search the web for recent papers", []) is AssistantMode.RESEARCH
    assert _detect_mode("open the browser and click the button", []) is AssistantMode.BROWSER
    assert _detect_mode("schedule a meeting tomorrow", []) is AssistantMode.SCHEDULING


def test_multimodal_request_contract():
    request = AssistantRequest(
        message="ఈ చిత్రాన్ని వివరించు",
        language="te-IN",
        session_id="session-1",
        attachments=[{"kind": "image", "name": "photo.jpg"}],
    )
    assert request.language == "te-IN"
    assert request.attachments[0]["kind"] == "image"

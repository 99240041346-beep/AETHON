from aethon.assistant_command_bridge import AssistantCommandBridge

def test_known_app_command_is_bounded():
    intent = AssistantCommandBridge().classify("open youtube")
    assert intent is not None
    assert intent.action == "android.open_app"
    assert intent.arguments["package"] == "com.google.android.youtube"

def test_unknown_package_is_not_authorized():
    assert AssistantCommandBridge().classify("open com.example.malware") is None

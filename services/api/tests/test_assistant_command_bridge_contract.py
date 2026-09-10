from aethon.assistant_command_bridge import AssistantCommandBridge


def test_allowlist_is_small_and_explicit():
    packages = AssistantCommandBridge.allowed_packages()
    assert packages["youtube"] == "com.google.android.youtube"
    assert packages["chrome"] == "com.android.chrome"
    assert packages["settings"] == "com.android.settings"
    assert all(value.startswith("com.") for value in packages.values())


def test_telugu_youtube_command_is_supported():
    intent = AssistantCommandBridge().classify("యూట్యూబ్")
    assert intent is None
    intent = AssistantCommandBridge().classify("ఓపెన్ యూట్యూబ్", language="te-IN")
    assert intent is not None
    assert intent.action == "android.open_app"
    assert intent.arguments["package"] == "com.google.android.youtube"

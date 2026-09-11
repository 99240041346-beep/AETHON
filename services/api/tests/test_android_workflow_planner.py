from app.android_workflow import MAX_WORKFLOW_STEPS, AndroidWorkflowPlanner


def test_settings_wifi_plan_is_bounded_and_ordered():
    planner = AndroidWorkflowPlanner()
    steps = planner.plan("Open Settings and go to Wi-Fi")
    encoded = planner.encode(steps)
    assert len(encoded) <= MAX_WORKFLOW_STEPS
    assert [step["capability"] for step in encoded] == ["OPEN_APP", "SCREEN_READ", "SCREEN_CLICK", "SCREEN_READ"]


def test_open_app_and_click_is_observe_act_observe():
    encoded = AndroidWorkflowPlanner().encode(AndroidWorkflowPlanner().plan("open Chrome and tap Search"))
    assert [step["capability"] for step in encoded] == ["OPEN_APP", "SCREEN_READ", "SCREEN_CLICK", "SCREEN_READ"]
    assert encoded[2]["arguments"] == {"text": "Search"}


def test_open_app_and_type_is_bounded():
    encoded = AndroidWorkflowPlanner().encode(AndroidWorkflowPlanner().plan("open Chrome and type hello world into Search"))
    assert [step["capability"] for step in encoded] == ["OPEN_APP", "SCREEN_READ", "SCREEN_TEXT", "SCREEN_READ"]
    assert encoded[2]["arguments"] == {"text": "Search", "value": "hello world"}


def test_scroll_and_back_are_observation_first():
    planner = AndroidWorkflowPlanner()
    assert [s.capability for s in planner.plan("scroll down")] == ["SCREEN_READ", "SCREEN_SCROLL", "SCREEN_READ"]
    assert [s.capability for s in planner.plan("go back")] == ["SCREEN_READ", "SCREEN_BACK", "SCREEN_READ"]


def test_verification_accepts_expected_visible_text():
    assert AndroidWorkflowPlanner.verify({"verify": {"contains_any": ["Wi-Fi network"]}}, {"nodes": [{"text": "Wi-Fi network", "package": "com.android.settings"}]})


def test_verification_rejects_missing_expected_text():
    assert not AndroidWorkflowPlanner.verify({"verify": {"contains_any": ["Wi-Fi network"]}}, {"nodes": [{"text": "Bluetooth", "package": "com.android.settings"}]})


def test_unsupported_workflow_is_rejected():
    try:
        AndroidWorkflowPlanner().plan("send a message to someone")
    except ValueError as exc:
        assert "no bounded Android workflow" in str(exc)
    else:
        raise AssertionError("unsupported workflow was accepted")

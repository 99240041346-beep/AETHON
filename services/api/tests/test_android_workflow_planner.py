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


def test_semantic_click_selects_exact_enabled_clickable_target():
    step = {"capability": "SCREEN_CLICK", "arguments": {"text": "Search"}}
    snapshot = {"connected": True, "nodes": [
        {"index": 1, "text": "Search", "class": "android.widget.Button", "clickable": True, "enabled": True},
    ]}
    candidate = AndroidWorkflowPlanner.select_action_candidate(step, snapshot)
    assert candidate is not None
    assert candidate["label"] == "Search"
    assert candidate["role"] == "button"


def test_disabled_semantic_target_is_ignored():
    step = {"capability": "SCREEN_CLICK", "arguments": {"text": "Search"}}
    snapshot = {"connected": True, "nodes": [
        {"text": "Search", "class": "android.widget.Button", "clickable": True, "enabled": False},
    ]}
    assert AndroidWorkflowPlanner.select_action_candidate(step, snapshot) is None


def test_text_action_requires_editable_target():
    step = {"capability": "SCREEN_TEXT", "arguments": {"text": "Search", "value": "hello"}}
    editable = {"connected": True, "nodes": [
        {"text": "Search", "class": "android.widget.EditText", "editable": True, "enabled": True},
    ]}
    non_editable = {"connected": True, "nodes": [
        {"text": "Search", "class": "android.widget.TextView", "enabled": True},
    ]}
    assert AndroidWorkflowPlanner.select_action_candidate(step, editable)["role"] == "text_field"
    assert AndroidWorkflowPlanner.select_action_candidate(step, non_editable) is None


def test_scroll_requires_scrollable_target():
    step = {"capability": "SCREEN_SCROLL", "arguments": {"text": "Content"}}
    snapshot = {"connected": True, "nodes": [
        {"text": "Content", "scrollable": True, "enabled": True},
    ]}
    assert AndroidWorkflowPlanner.select_action_candidate(step, snapshot)["role"] == "scroll_container"


def test_ambiguous_exact_matches_fail_closed():
    step = {"capability": "SCREEN_CLICK", "arguments": {"text": "Search"}}
    snapshot = {"connected": True, "nodes": [
        {"text": "Search", "class": "android.widget.Button", "clickable": True, "enabled": True},
        {"description": "Search", "class": "android.widget.Button", "clickable": True, "enabled": True},
    ]}
    assert AndroidWorkflowPlanner.select_action_candidate(step, snapshot) is None


def test_verification_accepts_expected_visible_text():
    assert AndroidWorkflowPlanner.verify({"verify": {"contains_any": ["Wi-Fi network"]}}, {"connected": True, "nodes": [{"text": "Wi-Fi network", "package": "com.android.settings"}]})


def test_verification_rejects_missing_expected_text():
    assert not AndroidWorkflowPlanner.verify({"verify": {"contains_any": ["Wi-Fi network"]}}, {"connected": True, "nodes": [{"text": "Bluetooth", "package": "com.android.settings"}]})


def test_unsupported_workflow_is_rejected():
    try:
        AndroidWorkflowPlanner().plan("send a message to someone")
    except ValueError as exc:
        assert "no bounded Android workflow" in str(exc)
    else:
        raise AssertionError("unsupported workflow was accepted")

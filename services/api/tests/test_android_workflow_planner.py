from app.android_workflow import MAX_WORKFLOW_STEPS, AndroidWorkflowPlanner


def test_settings_wifi_plan_is_bounded_and_ordered():
    planner = AndroidWorkflowPlanner()
    steps = planner.plan("Open Settings and go to Wi-Fi")
    encoded = planner.encode(steps)
    assert len(encoded) <= MAX_WORKFLOW_STEPS
    assert [step["capability"] for step in encoded] == [
        "OPEN_APP",
        "SCREEN_READ",
        "SCREEN_CLICK",
        "SCREEN_READ",
    ]


def test_verification_accepts_expected_visible_text():
    assert AndroidWorkflowPlanner.verify(
        {"verify": {"contains_any": ["Wi-Fi network"]}},
        {"nodes": [{"text": "Wi-Fi network", "package": "com.android.settings"}]},
    )


def test_verification_rejects_missing_expected_text():
    assert not AndroidWorkflowPlanner.verify(
        {"verify": {"contains_any": ["Wi-Fi network"]}},
        {"nodes": [{"text": "Bluetooth", "package": "com.android.settings"}]},
    )


def test_unsupported_workflow_is_rejected():
    try:
        AndroidWorkflowPlanner().plan("send a message to someone")
    except ValueError as exc:
        assert "no bounded Android workflow" in str(exc)
    else:
        raise AssertionError("unsupported workflow was accepted")

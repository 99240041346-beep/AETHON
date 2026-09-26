from app.android_ui_state import find_candidates, normalize_snapshot


def test_normalize_ui_roles_and_labels():
    state = normalize_snapshot({
        "connected": True,
        "node_count": 4,
        "nodes": [
            {"index": 0, "class": "android.widget.Button", "package": "com.example", "text": "Search", "clickable": True, "enabled": True},
            {"index": 1, "class": "android.widget.EditText", "package": "com.example", "description": "Search field", "editable": True, "enabled": True},
            {"index": 2, "class": "android.widget.ScrollView", "package": "com.example", "scrollable": True, "enabled": True},
            {"index": 3, "class": "android.widget.TextView", "package": "com.example", "text": "Results", "enabled": True},
        ],
    })
    assert [item["role"] for item in state["elements"]] == ["button", "text_field", "scroll_container", "text"]
    assert state["elements"][0]["label"] == "Search"
    assert state["elements"][1]["label"] == "Search field"


def test_find_candidates_uses_semantic_labels_only():
    state = normalize_snapshot({
        "connected": True,
        "nodes": [
            {"index": 0, "class": "android.widget.Button", "text": "Search", "clickable": True, "enabled": True},
            {"index": 1, "class": "android.widget.Button", "text": "Search", "clickable": True, "enabled": False},
        ],
    })
    candidates = find_candidates(state, "search")
    assert len(candidates) == 1
    assert candidates[0]["index"] == 0


def test_snapshot_is_bounded():
    state = normalize_snapshot({"connected": True, "nodes": [{"index": i, "text": str(i)} for i in range(500)]})
    assert len(state["elements"]) == 250
    assert state["node_count"] == 250


def test_disconnected_snapshot_is_safe():
    assert normalize_snapshot({"connected": False}) == {"connected": False, "node_count": 0, "elements": []}

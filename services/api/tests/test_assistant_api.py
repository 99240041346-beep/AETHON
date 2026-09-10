from fastapi.testclient import TestClient

from app.main import app


def test_assistant_chat_defaults_to_telugu_and_returns_session():
    client = TestClient(app)
    response = client.post("/v1/assistant/respond", json={"text": "హాయ్", "language": "te-IN"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["language"] == "te-IN"
    assert body["mode"] == "CHAT"
    assert body["session_id"]
    assert body["action_authorized"] is False


def test_assistant_action_is_not_authorized_by_classification_alone():
    client = TestClient(app)
    response = client.post("/v1/assistant/respond", json={"text": "ఓపెన్ YouTube", "language": "te-IN"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ACTION"
    assert body["intent"] == "android.open_app"
    assert body["action_authorized"] is False


def test_assistant_requires_confirmation_for_generic_side_effect_request():
    client = TestClient(app)
    response = client.post("/v1/assistant/respond", json={"text": "call my friend", "language": "en-US"})
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "ACTION"
    assert body["requires_confirmation"] is True
    assert body["action_authorized"] is False

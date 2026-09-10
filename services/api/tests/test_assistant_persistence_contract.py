from fastapi.testclient import TestClient

from app.main import app


def test_assistant_response_returns_normalized_detected_language():
    client = TestClient(app)
    response = client.post(
        "/v1/assistant/respond",
        json={"text": "నమస్కారం", "language": "en-US"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "te-IN"
    assert body["session_id"]
    assert body["action_authorized"] is False


def test_assistant_response_returns_same_english_locale():
    client = TestClient(app)
    response = client.post(
        "/v1/assistant/respond",
        json={"text": "Hello AETHON", "language": "en-US"},
    )
    assert response.status_code == 200
    assert response.json()["language"] == "en-US"


def test_assistant_history_endpoint_is_owner_scoped_contract():
    client = TestClient(app)
    response = client.get("/v1/assistant/sessions/00000000-0000-0000-0000-000000000001/messages")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

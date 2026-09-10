from fastapi.testclient import TestClient

from app.main import app


def test_voice_endpoint_round_trip(monkeypatch):
    class Provider:
        name = "test"
        def generate(self, prompt):
            assert "Respond naturally in Telugu" in prompt
            return "నమస్కారం! నేను AETHON."
        def health(self):
            return True

    monkeypatch.setattr("aethon.voice_api.model_router", type("R", (), {"provider": Provider(), "generate": lambda self, prompt: self.provider.generate(prompt)})())
    client = TestClient(app)
    response = client.post("/v1/voice/respond", json={"transcript": "నాకు సహాయం చేయి", "language": "te-IN"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["language"] == "te-IN"
    assert data["action_authorized"] is False
    assert data["response"] == "నమస్కారం! నేను AETHON."


def test_voice_endpoint_returns_allowlisted_android_action():
    client = TestClient(app)
    response = client.post("/v1/voice/respond", json={"transcript": "open youtube", "language": "en-US"})
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "command-bridge"
    assert data["action_authorized"] is True
    assert data["action"] == "android.open_app"
    assert data["action_package"] == "com.google.android.youtube"


def test_voice_endpoint_does_not_authorize_arbitrary_android_package():
    client = TestClient(app)
    response = client.post("/v1/voice/respond", json={"transcript": "open com.example.anything", "language": "en-US"})
    assert response.status_code == 200
    assert response.json()["action_authorized"] is False
    assert response.json()["action"] is None

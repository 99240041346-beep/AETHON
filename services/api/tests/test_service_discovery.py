from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_discovery():
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["service"] == "aethon-api"
    assert payload["capabilities"] == "/v1/capabilities"


def test_health_reports_version():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["service"] == "aethon-api"


def test_capabilities_are_truthful():
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    names = {item["name"] for item in payload["capabilities"]}
    assert {"CHAT", "CALCULATOR", "WEB_SEARCH", "WEB_FETCH"} <= names

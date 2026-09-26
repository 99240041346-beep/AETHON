from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.assistant_runtime_api as runtime_api
from app.main import app


class FakeRuntime:
    def run(self, **kwargs):
        event = SimpleNamespace(
            type="runtime.completed",
            request_id=kwargs.get("request_id") or "req-test",
            data={"stage": "response"},
        )
        callback = kwargs.get("event_callback")
        if callback is not None:
            callback(event)
        return SimpleNamespace(
            error=None,
            request_id=event.request_id,
            session_id=kwargs.get("session_id") or "session-test",
            mode="CHAT",
            intent=SimpleNamespace(action="chat"),
            response="test response",
            requires_confirmation=False,
            action_authorized=False,
            verified=False,
            events=[event],
        )


def client(monkeypatch):
    monkeypatch.setattr(runtime_api, "runtime", FakeRuntime())
    app.dependency_overrides[runtime_api.owner] = lambda: "owner-test"
    return TestClient(app)


def test_runtime_respond_is_authenticated_and_returns_contract(monkeypatch):
    test_client = client(monkeypatch)
    try:
        response = test_client.post(
            "/v1/assistant/runtime/respond",
            json={"text": "Hello", "language": "en-IN"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["request_id"]
    assert body["session_id"] == "session-test"
    assert body["response"] == "test response"
    assert body["events"][0]["type"] == "runtime.completed"


def test_runtime_respond_rejects_missing_authentication(monkeypatch):
    monkeypatch.setattr(runtime_api, "runtime", FakeRuntime())
    monkeypatch.setenv("AETHON_API_TOKEN", "test-secret")
    response = TestClient(app).post(
        "/v1/assistant/runtime/respond",
        json={"text": "Hello", "language": "en-IN"},
    )

    assert response.status_code == 401


def test_runtime_respond_accepts_configured_bearer_token(monkeypatch):
    test_client = client(monkeypatch)
    monkeypatch.setenv("AETHON_API_TOKEN", "test-secret")
    try:
        response = test_client.post(
            "/v1/assistant/runtime/respond",
            headers={"Authorization": "Bearer test-secret"},
            json={"text": "Hello", "language": "en-IN"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_runtime_stream_emits_started_progress_and_completed(monkeypatch):
    test_client = client(monkeypatch)
    try:
        response = test_client.post(
            "/v1/assistant/runtime/stream",
            json={"text": "Hello", "language": "en-IN"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in response.text
    assert "event: progress" in response.text
    assert "event: completed" in response.text
    assert '"request_id": "' in response.text


def test_runtime_stream_does_not_leak_exception_details(monkeypatch):
    class BrokenRuntime:
        def run(self, **kwargs):
            raise RuntimeError("SECRET_INTERNAL_DETAIL")

    monkeypatch.setattr(runtime_api, "runtime", BrokenRuntime())
    app.dependency_overrides[runtime_api.owner] = lambda: "owner-test"
    try:
        response = TestClient(app).post(
            "/v1/assistant/runtime/stream",
            json={"text": "Hello", "language": "en-IN"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "assistant runtime unavailable" in response.text
    assert "SECRET_INTERNAL_DETAIL" not in response.text


def _events(body: str):
    events = []
    for block in body.split("\n\n"):
        if "data: " not in block:
            continue
        raw = block.split("data: ", 1)[1].strip()
        events.append(json.loads(raw))
    return events


def test_runtime_stream_payloads_are_valid_json_and_share_request_id(monkeypatch):
    test_client = client(monkeypatch)
    try:
        response = test_client.post(
            "/v1/assistant/runtime/stream",
            json={"text": "Hello", "language": "en-IN"},
        )
    finally:
        app.dependency_overrides.clear()

    events = _events(response.text)
    request_ids = [event.get("request_id") for event in events if event.get("request_id")]
    assert events[0]["status"] == "started"
    assert events[-1]["ok"] is True
    assert len(set(request_ids)) == 1
    assert events[-1]["request_id"] == events[0]["request_id"]


def test_runtime_request_rejects_unknown_fields(client):
    response = client.post("/v1/assistant/runtime/respond", json={"text": "hello", "unexpected": True})
    assert response.status_code == 422

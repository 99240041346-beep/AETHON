import os

from fastapi.testclient import TestClient

from aethon.main import app


def test_owner_isolation_in_memory_api(monkeypatch):
    monkeypatch.delenv("AETHON_API_TOKEN", raising=False)
    monkeypatch.setenv("AETHON_API_OWNER_ID", "owner-a")
    client = TestClient(app)
    created = client.post('/v1/memory', json={
        'memory_id': 'owner-a-memory', 'content': 'private project context',
        'project_id': 'project-a', 'namespace': 'project'
    })
    assert created.status_code == 200

    monkeypatch.setenv("AETHON_API_OWNER_ID", "owner-b")
    hidden = client.post('/v1/memory/search', json={
        'query': 'private project context', 'project_id': 'project-a', 'namespace': 'project'
    })
    assert hidden.status_code == 200
    assert hidden.json() == []


def test_configured_bearer_token_is_required(monkeypatch):
    monkeypatch.setenv("AETHON_API_TOKEN", "test-token")
    monkeypatch.setenv("AETHON_API_OWNER_ID", "owner-a")
    client = TestClient(app)
    unauthenticated = client.post('/v1/memory/search', json={'query': 'x'})
    assert unauthenticated.status_code == 401
    authenticated = client.post('/v1/memory/search', json={'query': 'x'}, headers={'Authorization': 'Bearer test-token'})
    assert authenticated.status_code == 200
    monkeypatch.delenv("AETHON_API_TOKEN", raising=False)

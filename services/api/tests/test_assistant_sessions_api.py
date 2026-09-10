from fastapi.testclient import TestClient

from app.main import app


def test_assistant_session_lifecycle():
    client = TestClient(app)
    response = client.post('/v1/assistant/respond', json={'text': 'హాయ్', 'language': 'te-IN'})
    assert response.status_code == 200
    session_id = response.json()['session_id']

    listed = client.get('/v1/assistant/sessions')
    assert listed.status_code == 200
    assert any(item['session_id'] == session_id for item in listed.json())

    detail = client.get(f'/v1/assistant/sessions/{session_id}')
    assert detail.status_code == 200
    assert detail.json()['session_id'] == session_id

    messages = client.get(f'/v1/assistant/sessions/{session_id}/messages')
    assert messages.status_code == 200
    assert [item['role'] for item in messages.json()] == ['user', 'assistant']

    archived = client.delete(f'/v1/assistant/sessions/{session_id}')
    assert archived.status_code == 200
    assert archived.json()['archived'] is True


def test_assistant_session_invalid_uuid_is_rejected():
    client = TestClient(app)
    response = client.get('/v1/assistant/sessions/not-a-uuid')
    assert response.status_code == 400

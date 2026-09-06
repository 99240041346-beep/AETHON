from fastapi.testclient import TestClient
from aethon.main import app

client = TestClient(app)


def test_memory_write_search_and_delete():
    payload = {
        'memory_id': 'api-test-memory',
        'content': 'AETHON project uses persistent memory',
        'project_id': 'api-project',
        'namespace': 'project',
        'confidence': 0.9,
    }
    created = client.post('/v1/memory', json=payload)
    assert created.status_code == 200
    found = client.post('/v1/memory/search', json={
        'query': 'persistent memory', 'project_id': 'api-project', 'namespace': 'project'
    })
    assert found.status_code == 200
    assert found.json()[0]['memory_id'] == 'api-test-memory'
    deleted = client.request('DELETE', '/v1/memory/api-test-memory', json={
        'project_id': 'api-project', 'namespace': 'project'
    })
    assert deleted.status_code == 200


def test_memory_scope_isolation():
    client.post('/v1/memory', json={
        'memory_id': 'isolated-memory', 'content': 'alpha-only',
        'project_id': 'alpha', 'namespace': 'project'
    })
    found = client.post('/v1/memory/search', json={
        'query': 'alpha-only', 'project_id': 'beta', 'namespace': 'project'
    })
    assert found.status_code == 200
    assert found.json() == []

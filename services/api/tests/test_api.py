from fastapi.testclient import TestClient
from aethon.main import app

client = TestClient(app)

def test_health():
    r = client.get('/health'); assert r.status_code == 200 and r.json()['ok'] is True

def test_task_vertical_slice():
    r = client.post('/v1/tasks', json={'goal':'hello AETHON'})
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'SUCCEEDED'
    assert 'AETHON received' in body['result']
    task_id = body['task_id']
    events = client.get(f'/v1/tasks/{task_id}/events').json()
    assert [e['data'].get('status') for e in events if e['type']=='task.state_changed'] == ['PLANNING','EXECUTING','VERIFYING','SUCCEEDED']

def test_calculator_safe():
    r = client.post('/v1/tools/execute', json={'tool':'calculator','arguments':{'expression':'2 + 3 * 4'}})
    assert r.status_code == 200 and r.json()['output'] == 14

def test_calculator_rejects_code():
    r = client.post('/v1/tools/execute', json={'tool':'calculator','arguments':{'expression':'__import__("os").getcwd()'}})
    assert r.status_code == 200 and r.json()['ok'] is False

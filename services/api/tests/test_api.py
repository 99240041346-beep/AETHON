import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from aethon.agent import AgentRuntime
from aethon.main import app
from aethon.store import TaskStore
from aethon.verification import VerificationResult

client = TestClient(app)


def test_health():
    r = client.get('/health')
    assert r.status_code == 200 and r.json()['ok'] is True


def test_task_vertical_slice_and_audit():
    with tempfile.TemporaryDirectory() as tmp:
        store = TaskStore(str(Path(tmp) / 'aethon.db'))
        result = store.create(__import__('aethon.schemas', fromlist=['TaskCreate']).TaskCreate(goal='hello AETHON'))
        assert result.status.value == 'SUCCEEDED'
        assert 'AETHON received' in result.result
        events = store.events(result.task_id)
        assert [e.data.get('status') for e in events if e.type == 'task.state_changed'] == ['PLANNING', 'EXECUTING', 'VERIFYING', 'EXECUTING', 'SUCCEEDED']
        audit = store.audit(result.task_id)
        assert any(e['action'] == 'verification' and e['data']['ok'] is True for e in audit)


def test_verification_failure_blocks_success():
    class AlwaysFailVerifier:
        def verify(self, goal, result):
            return VerificationResult(False, 'test failure', {})

    from aethon.schemas import Task
    runtime = AgentRuntime(verifier=AlwaysFailVerifier())
    task = runtime.run(Task(goal='must fail verification'))
    assert task.status.value == 'BLOCKED'
    assert 'replan budget exhausted' in task.error


def test_persistence_survives_new_store_instance():
    with tempfile.TemporaryDirectory() as tmp:
        db = str(Path(tmp) / 'aethon.db')
        first = TaskStore(db)
        created = first.create(__import__('aethon.schemas', fromlist=['TaskCreate']).TaskCreate(goal='durable task'))
        second = TaskStore(db)
        loaded = second.get(created.task_id)
        assert loaded is not None
        assert loaded.status.value == 'SUCCEEDED'
        assert loaded.result == created.result
        assert len(second.events(created.task_id)) >= 4


def test_calculator_safe():
    r = client.post('/v1/tools/execute', json={'tool': 'calculator', 'arguments': {'expression': '2 + 3 * 4'}})
    assert r.status_code == 200 and r.json()['output'] == 14


def test_calculator_rejects_code():
    r = client.post('/v1/tools/execute', json={'tool': 'calculator', 'arguments': {'expression': '__import__("os").getcwd()'}})
    assert r.status_code == 200 and r.json()['ok'] is False

from uuid import uuid4

import pytest

from aethon.pg_task_store import PostgreSQLTaskStore
from aethon.schemas import Task, TaskStatus


class FakeStore:
    def __init__(self, rows):
        self.database_url = "postgresql://test"
        self.rows = rows
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((query, params))
        return self.rows


def test_get_task_maps_postgres_row():
    task_id = uuid4()
    store = PostgreSQLTaskStore.__new__(PostgreSQLTaskStore)
    store.store = FakeStore([(task_id, "do work", "p1", "u1", 2, "EXECUTING", {"ok": True}, None)])
    task = store.get_task(task_id)
    assert task is not None
    assert task.task_id == task_id
    assert task.status is TaskStatus.EXECUTING
    assert task.result == {"ok": True}


def test_recoverable_tasks_excludes_approval_and_paused_by_contract():
    ids = [uuid4(), uuid4()]
    store = PostgreSQLTaskStore.__new__(PostgreSQLTaskStore)
    store.store = FakeStore([(ids[0],), (ids[1],)])
    assert store.recoverable_tasks() == ids
    query = store.store.calls[-1][0]
    assert "status IN ('QUEUED','EXECUTING','REPLANNING','VERIFYING')" in query
    assert "AWAITING_APPROVAL" not in query
    assert "PAUSED" not in query
    assert "expires_at <= NOW()" in query


def test_put_task_uses_upsert():
    task = Task(goal="persist me")
    store = PostgreSQLTaskStore.__new__(PostgreSQLTaskStore)
    store.store = FakeStore([(task.task_id, task.goal, None, task.owner_id, task.priority, "QUEUED", None, None)])
    result = store.put_task(task)
    assert result.task_id == task.task_id
    assert "ON CONFLICT(task_id) DO UPDATE" in store.store.calls[-1][0]


def test_claim_validation():
    store = PostgreSQLTaskStore.__new__(PostgreSQLTaskStore)
    with pytest.raises(ValueError):
        store.claim_task("", 30)
    with pytest.raises(ValueError):
        store.claim_task("worker", 0)


def test_heartbeat_and_release_require_positive_lease():
    store = PostgreSQLTaskStore.__new__(PostgreSQLTaskStore)
    with pytest.raises(ValueError):
        store.heartbeat(uuid4(), "worker", "token", 0)
    store.store = FakeStore([])
    with pytest.raises(ValueError):
        store.heartbeat(uuid4(), "worker", "token", 0)

from __future__ import annotations

import sqlite3
from concurrent.futures import Future
from pathlib import Path
from uuid import uuid4

from app.schemas import TaskStatus
from app.store import TaskStore


class FakeStateStore:
    def __init__(self, states=None):
        self.states = states or {}

    def load(self, task_id):
        return self.states.get(task_id)


class FakeLeaseStore:
    def __init__(self, leases=None):
        self.leases = leases or {}

    def get(self, task_id):
        return self.leases.get(task_id)


class FakeRuntime:
    def __init__(self):
        self.events = {}

    def _event(self, task, event_type, data):
        self.events.setdefault(task.task_id, []).append((event_type, data))


def make_store(tmp_path: Path, lease):
    db = tmp_path / "tasks.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, goal TEXT, project_id TEXT, priority INTEGER, owner_id TEXT, status TEXT, result_json TEXT, error TEXT, created_at TEXT, updated_at TEXT)")
        conn.execute(
            "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
            (str(uuid4()), "goal", None, 5, "owner", TaskStatus.EXECUTING.value, None, None, "1", "1"),
        )
    store = TaskStore.__new__(TaskStore)
    store.database_path = db
    store.state_store = FakeStateStore()
    store.lease_store = lease
    store.runtime = FakeRuntime()
    store.worker_id = "worker-b"
    store._futures = {}
    store._future_lock = __import__("threading").Lock()
    return store, db


def test_restart_recovery_skips_task_owned_by_live_worker(tmp_path):
    db = tmp_path / "tasks.db"
    task_id = uuid4()
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, goal TEXT, project_id TEXT, priority INTEGER, owner_id TEXT, status TEXT, result_json TEXT, error TEXT, created_at TEXT, updated_at TEXT)")
        conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)", (str(task_id), "goal", None, 5, "owner", TaskStatus.EXECUTING.value, None, None, "1", "1"))

    lease = FakeLeaseStore({str(task_id): {"worker_id": "worker-a", "expired": False}})
    store = TaskStore.__new__(TaskStore)
    store.database_path = db
    store.state_store = FakeStateStore({task_id: object()})
    store.lease_store = lease
    store.runtime = FakeRuntime()
    store.worker_id = "worker-b"
    store._futures = {}
    import threading
    store._future_lock = threading.Lock()
    submitted = []
    store._submit = lambda task: submitted.append(task) or Future()
    store._persist_task = lambda task: None
    store._persist_events = lambda task_id: None

    store._recover_tasks()

    assert submitted == []


def test_restart_recovery_admits_expired_or_unleased_task(tmp_path):
    db = tmp_path / "tasks.db"
    task_id = uuid4()
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE tasks (task_id TEXT PRIMARY KEY, goal TEXT, project_id TEXT, priority INTEGER, owner_id TEXT, status TEXT, result_json TEXT, error TEXT, created_at TEXT, updated_at TEXT)")
        conn.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)", (str(task_id), "goal", None, 5, "owner", TaskStatus.EXECUTING.value, None, None, "1", "1"))

    store = TaskStore.__new__(TaskStore)
    store.database_path = db
    store.state_store = FakeStateStore({task_id: object()})
    store.lease_store = FakeLeaseStore({str(task_id): {"worker_id": "dead-worker", "expired": True}})
    store.runtime = FakeRuntime()
    store.worker_id = "worker-b"
    store._futures = {}
    import threading
    store._future_lock = threading.Lock()
    submitted = []
    future = Future()
    future.set_result(None)
    store._submit = lambda task: submitted.append(task) or future
    store._persist_task = lambda task: None
    store._persist_events = lambda task_id: None

    store._recover_tasks()

    assert [task.task_id for task in submitted] == [task_id]

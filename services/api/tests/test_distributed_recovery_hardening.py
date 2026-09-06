from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.distributed_persistence import DistributedTaskPersistence


class FakeStore:
    def __init__(self):
        self.rows = []
        self.acquire_calls = []

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).lower()
        if normalized.startswith("select task_id, worker_id, lease_token, expires_at"):
            return list(self.rows)
        if normalized.startswith("select t.task_id"):
            return [(row[0],) for row in self.rows if row[4]]
        raise AssertionError(sql)


def test_recovery_query_excludes_live_leases():
    persistence = DistributedTaskPersistence.__new__(DistributedTaskPersistence)
    persistence.store = FakeStore()
    task_id = uuid4()
    persistence.store.rows = [
        (task_id, "worker-a", "token", datetime.now(timezone.utc), None, False),
    ]
    assert persistence.recoverable_tasks() == []


def test_recovery_query_includes_expired_or_unleased_task():
    persistence = DistributedTaskPersistence.__new__(DistributedTaskPersistence)
    persistence.store = FakeStore()
    task_id = uuid4()
    persistence.store.rows = [
        (task_id, "worker-a", "token", datetime.now(timezone.utc), None, True),
    ]
    assert persistence.recoverable_tasks() == [task_id]


def test_acquire_lease_rejects_invalid_inputs():
    persistence = DistributedTaskPersistence.__new__(DistributedTaskPersistence)
    with pytest.raises(ValueError):
        persistence.acquire_lease(uuid4(), "", 30)
    with pytest.raises(ValueError):
        persistence.acquire_lease(uuid4(), "worker", 0)

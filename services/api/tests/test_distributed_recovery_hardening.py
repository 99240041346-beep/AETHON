from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.distributed_persistence import DistributedTaskPersistence, RecoveryCandidate


class FakeStore:
    def __init__(self):
        self.recoverable_rows = []
        self.lease_rows = []
        self.sql = []

    def execute(self, sql, params=None):
        normalized = " ".join(sql.split()).lower()
        self.sql.append(normalized)
        if normalized.startswith("select t.task_id"):
            return list(self.recoverable_rows)
        if normalized.startswith("select task_id, worker_id, lease_token, expires_at"):
            return list(self.lease_rows)
        raise AssertionError(sql)


def make_persistence(store: FakeStore) -> DistributedTaskPersistence:
    persistence = DistributedTaskPersistence.__new__(DistributedTaskPersistence)
    persistence.store = store
    return persistence


def test_recovery_query_excludes_live_leases_and_approval_tasks():
    store = FakeStore()
    persistence = make_persistence(store)
    assert persistence.recoverable_tasks() == []
    query = store.sql[-1]
    assert "awaiting_approval" not in query
    assert "expires_at <= now()" in query


def test_recovery_candidate_preserves_previous_lease_identity():
    task_id = uuid4()
    expired = datetime.now(timezone.utc)
    candidate = RecoveryCandidate(task_id, "dead-worker", "old-token", expired)
    assert candidate.task_id == task_id
    assert candidate.worker_id == "dead-worker"
    assert candidate.lease_token == "old-token"
    assert candidate.expired_at == expired


def test_acquire_lease_rejects_invalid_inputs_without_connecting():
    persistence = make_persistence(FakeStore())
    with pytest.raises(ValueError, match="worker_id"):
        persistence.acquire_lease(uuid4(), "", 30)
    with pytest.raises(ValueError, match="lease_seconds"):
        persistence.acquire_lease(uuid4(), "worker", 0)


def test_configured_accepts_postgres_urls(monkeypatch):
    monkeypatch.setenv("AETHON_DATABASE_URL", "postgresql://user:pass@db/aethon")
    assert DistributedTaskPersistence.configured() is True
    monkeypatch.setenv("AETHON_DATABASE_URL", "sqlite:///aethon.db")
    assert DistributedTaskPersistence.configured() is False

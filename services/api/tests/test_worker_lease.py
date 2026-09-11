import time

import pytest

from aethon.worker_lease import LeaseConflict, WorkerLeaseStore


def test_lease_prevents_duplicate_worker_ownership(tmp_path):
    store = WorkerLeaseStore(str(tmp_path / "leases.db"))
    token = store.acquire("task-1", "worker-a", ttl_seconds=1.0)
    with pytest.raises(LeaseConflict):
        store.acquire("task-1", "worker-b", ttl_seconds=1.0)
    assert store.heartbeat("task-1", "worker-a", token, ttl_seconds=1.0)
    assert store.release("task-1", "worker-a", token)
    assert store.get("task-1") is None


def test_expired_lease_can_be_recovered(tmp_path):
    store = WorkerLeaseStore(str(tmp_path / "leases.db"))
    store.acquire("task-2", "worker-a", ttl_seconds=0.01)
    time.sleep(0.03)
    assert store.recover_expired() == 1
    token = store.acquire("task-2", "worker-b", ttl_seconds=0.2)
    assert store.get("task-2")["worker_id"] == "worker-b"
    assert store.release("task-2", "worker-b", token)


def test_wrong_worker_cannot_heartbeat_or_release(tmp_path):
    store = WorkerLeaseStore(str(tmp_path / "leases.db"))
    token = store.acquire("task-3", "worker-a")
    assert not store.heartbeat("task-3", "worker-b", token)
    assert not store.release("task-3", "worker-b", token)
    assert store.release("task-3", "worker-a", token)

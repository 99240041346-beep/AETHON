import time

import pytest

from aethon.worker_lease import WorkerLeaseStore
from aethon.worker_pool import LeasedWorkerPool


def test_leased_pool_acquires_heartbeats_and_releases(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    seen = []
    pool = LeasedWorkerPool(lambda value: seen.append(value) or value * 2, leases, "worker-a", lease_seconds=0.08, heartbeat_seconds=0.02)
    assert pool.run("task-1", 21) == 42
    assert seen == [21]
    assert leases.get("task-1") is None


def test_leased_pool_rejects_duplicate_worker(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    leases.acquire("task-2", "worker-b", ttl_seconds=0.2)
    pool = LeasedWorkerPool(lambda value: value, leases, "worker-a", lease_seconds=0.2, heartbeat_seconds=0.05)
    with pytest.raises(Exception, match="another worker"):
        pool.run("task-2", 1)


def test_lease_expiry_is_recoverable(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    leases.acquire("task-3", "worker-a", ttl_seconds=0.01)
    time.sleep(0.03)
    assert leases.recover_expired() == 1
    pool = LeasedWorkerPool(lambda value: value + 1, leases, "worker-b", lease_seconds=0.1, heartbeat_seconds=0.02)
    assert pool.run("task-3", 4) == 5

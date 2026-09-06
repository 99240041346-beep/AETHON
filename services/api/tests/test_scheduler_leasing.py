import threading
import time

import pytest

from aethon.scheduler import TaskScheduler
from aethon.worker_lease import LeaseConflict, WorkerLeaseStore
from aethon.worker_pool import LeasedWorkerPool


def test_scheduler_executes_through_worker_lease(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    seen = []
    pool = LeasedWorkerPool(lambda value: seen.append(value) or value.upper(), leases, "worker-a", lease_seconds=0.2, heartbeat_seconds=0.05)
    scheduler = TaskScheduler(lambda value: value, max_workers=1, worker_pool=pool, lease_key=lambda value: value)
    try:
        future = scheduler.submit("task-1")
        assert future.result(timeout=2) == "TASK-1"
        assert seen == ["task-1"]
        assert leases.get("task-1") is None
        assert scheduler.snapshot()["leased_execution"] is True
    finally:
        scheduler.shutdown()


def test_scheduler_propagates_lease_conflict(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    leases.acquire("task-1", "other-worker", ttl_seconds=1)
    pool = LeasedWorkerPool(lambda value: value, leases, "worker-a", lease_seconds=0.2, heartbeat_seconds=0.05)
    scheduler = TaskScheduler(lambda value: value, max_workers=1, worker_pool=pool, lease_key=lambda value: value)
    try:
        future = scheduler.submit("task-1")
        with pytest.raises(LeaseConflict):
            future.result(timeout=2)
    finally:
        scheduler.shutdown()


def test_heartbeat_keeps_lease_alive_during_long_work(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    started = threading.Event()

    def work(value):
        started.set()
        time.sleep(0.18)
        return value

    pool = LeasedWorkerPool(work, leases, "worker-a", lease_seconds=0.08, heartbeat_seconds=0.02)
    assert pool.run("task-1", "ok") == "ok"
    assert started.is_set()
    assert leases.get("task-1") is None

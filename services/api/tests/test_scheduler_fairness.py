import threading
import time

import pytest

from aethon.scheduler import TaskScheduler


def test_queue_has_a_hard_bound():
    gate = threading.Event()
    scheduler = TaskScheduler(lambda value: gate.wait(timeout=1) or value, max_workers=1, max_queue=2)
    try:
        scheduler.submit("active")
        time.sleep(0.02)
        scheduler.submit("queued-1")
        scheduler.submit("queued-2")
        with pytest.raises(RuntimeError, match="queue is full"):
            scheduler.submit("overflow")
    finally:
        gate.set()
        scheduler.shutdown()


def test_priority_aging_promotes_long_waiting_work():
    started = []
    gate = threading.Event()

    def worker(value):
        started.append(value)
        if value == "blocker":
            gate.wait(timeout=1)
        return value

    scheduler = TaskScheduler(worker, max_workers=1, aging_seconds=0.01)
    try:
        blocker = scheduler.submit("blocker", priority=5)
        time.sleep(0.02)
        low = scheduler.submit("low", priority=10)
        time.sleep(0.04)
        high = scheduler.submit("high", priority=1)
        gate.set()
        assert blocker.result(timeout=2) == "blocker"
        assert low.result(timeout=2) == "low"
        assert high.result(timeout=2) == "high"
        assert started[:2] == ["blocker", "low"]
    finally:
        scheduler.shutdown()


def test_scheduler_snapshot_exposes_capacity_controls():
    gate = threading.Event()
    scheduler = TaskScheduler(lambda value: gate.wait(timeout=1) or value, max_workers=1, max_queue=3, aging_seconds=5)
    try:
        scheduler.submit("active")
        time.sleep(0.02)
        scheduler.submit("queued")
        snapshot = scheduler.snapshot()
        assert snapshot == {
            "queued": 1,
            "active": 1,
            "max_workers": 1,
            "max_queue": 3,
            "aging_seconds": 5,
            "resource_limits": {},
            "resources_in_use": {},
        }
    finally:
        gate.set()
        scheduler.shutdown()


def test_scheduler_rejects_invalid_capacity_configuration():
    with pytest.raises(ValueError):
        TaskScheduler(lambda value: value, max_queue=0)
    with pytest.raises(ValueError):
        TaskScheduler(lambda value: value, aging_seconds=0)

import threading
import time

import pytest

from aethon.scheduler import TaskScheduler


def test_scheduler_aging_prevents_starvation():
    started = []
    gate = threading.Event()

    def worker(value):
        started.append(value)
        if value == "running":
            gate.wait(timeout=1)
        return value

    scheduler = TaskScheduler(worker, max_workers=1, aging_seconds=0.02)
    try:
        running = scheduler.submit("running", priority=5)
        time.sleep(0.01)
        old = scheduler.submit("old", priority=2)
        high = scheduler.submit("high", priority=1)
        time.sleep(0.03)
        gate.set()
        assert running.result(timeout=2) == "running"
        assert old.result(timeout=2) == "old"
        assert high.result(timeout=2) == "high"
        assert started[:2] == ["running", "old"]
    finally:
        scheduler.shutdown()


def test_scheduler_bounds_queued_admission():
    gate = threading.Event()

    def worker(value):
        gate.wait(timeout=1)
        return value

    scheduler = TaskScheduler(worker, max_workers=1, max_queue=2)
    try:
        first = scheduler.submit("first")
        time.sleep(0.02)
        scheduler.submit("second")
        scheduler.submit("third")
        with pytest.raises(RuntimeError, match="queue is full"):
            scheduler.submit("fourth")
        gate.set()
        assert first.result(timeout=2) == "first"
    finally:
        gate.set()
        scheduler.shutdown()

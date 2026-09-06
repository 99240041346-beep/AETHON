import threading
import time

from aethon.scheduler import TaskScheduler


def test_scheduler_runs_tasks_concurrently():
    active = 0
    peak = 0
    lock = threading.Lock()

    def worker(value):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return value * 2

    scheduler = TaskScheduler(worker, max_workers=2)
    try:
        futures = [scheduler.submit(i) for i in range(3)]
        assert [future.result(timeout=2) for future in futures] == [0, 2, 4]
        assert peak == 2
    finally:
        scheduler.shutdown()


def test_scheduler_honors_priority_then_fifo():
    started = []
    gate = threading.Event()

    def worker(value):
        started.append(value)
        if value == "first":
            gate.wait(timeout=1)
        return value

    scheduler = TaskScheduler(worker, max_workers=1)
    try:
        first = scheduler.submit("first", priority=5)
        time.sleep(0.02)
        high = scheduler.submit("high", priority=1)
        normal = scheduler.submit("normal", priority=5)
        gate.set()
        assert first.result(timeout=2) == "first"
        assert high.result(timeout=2) == "high"
        assert normal.result(timeout=2) == "normal"
        assert started == ["first", "high", "normal"]
    finally:
        scheduler.shutdown()


def test_scheduler_rejects_invalid_priority():
    scheduler = TaskScheduler(lambda value: value, max_workers=1)
    try:
        try:
            scheduler.submit("x", priority=11)
            assert False, "expected ValueError"
        except ValueError:
            pass
    finally:
        scheduler.shutdown()

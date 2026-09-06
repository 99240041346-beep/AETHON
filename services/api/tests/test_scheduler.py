import threading
import time

import pytest

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


def test_scheduler_waits_for_dependencies():
    started = []
    scheduler = TaskScheduler(lambda value: started.append(value) or value, max_workers=2)
    try:
        first = scheduler.submit("first")
        dependent = scheduler.submit("dependent", priority=1, dependencies=[first])
        assert dependent.result(timeout=2) == "dependent"
        assert started == ["first", "dependent"]
    finally:
        scheduler.shutdown()


def test_scheduler_skips_blocked_dependency_for_ready_work():
    started = []
    gate = threading.Event()

    def worker(value):
        started.append(value)
        if value == "slow":
            gate.wait(timeout=1)
        return value

    scheduler = TaskScheduler(worker, max_workers=1)
    try:
        slow = scheduler.submit("slow", priority=5)
        dependent = scheduler.submit("dependent", priority=1, dependencies=[slow])
        independent = scheduler.submit("independent", priority=2)
        assert independent.result(timeout=2) == "independent"
        gate.set()
        assert slow.result(timeout=2) == "slow"
        assert dependent.result(timeout=2) == "dependent"
        assert started == ["independent", "slow", "dependent"]
    finally:
        scheduler.shutdown()


def test_scheduler_enforces_resource_quota():
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
        return value

    scheduler = TaskScheduler(worker, max_workers=3, resource_limits={"gpu": 1})
    try:
        futures = [scheduler.submit(i, resources={"gpu": 1}) for i in range(3)]
        assert [future.result(timeout=3) for future in futures] == [0, 1, 2]
        assert peak == 1
    finally:
        scheduler.shutdown()


def test_scheduler_rejects_invalid_priority_and_resource_requests():
    scheduler = TaskScheduler(lambda value: value, max_workers=1, resource_limits={"cpu": 2})
    try:
        with pytest.raises(ValueError):
            scheduler.submit("x", priority=11)
        with pytest.raises(ValueError):
            scheduler.submit("x", resources={"cpu": 3})
        with pytest.raises(ValueError):
            scheduler.submit("x", resources={"gpu": 1})
    finally:
        scheduler.shutdown()

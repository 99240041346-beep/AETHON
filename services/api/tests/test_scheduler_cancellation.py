import threading
import time
from uuid import uuid4

from aethon.agent_state import AgentStateStore
from aethon.scheduler import TaskScheduler


def test_queued_future_can_be_cancelled_before_worker_admission():
    gate = threading.Event()
    started = []

    def worker(value):
        started.append(value)
        if value == "first":
            gate.wait(timeout=2)
        return value

    scheduler = TaskScheduler(worker, max_workers=1)
    try:
        first = scheduler.submit("first")
        second = scheduler.submit("second")
        time.sleep(0.03)
        assert second.cancel() is True
        gate.set()
        assert first.result(timeout=2) == "first"
        assert second.cancelled()
        assert started == ["first"]
    finally:
        scheduler.shutdown()


def test_cancel_control_survives_state_store_restart(tmp_path):
    task_id = uuid4()
    path = tmp_path / "state.db"
    first = AgentStateStore(str(path))
    first.request_cancel(task_id)
    assert first.cancel_requested(task_id)

    restarted = AgentStateStore(str(path))
    assert restarted.cancel_requested(task_id)
    restarted.clear_controls(task_id)
    assert not restarted.cancel_requested(task_id)

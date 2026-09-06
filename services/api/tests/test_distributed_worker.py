from uuid import uuid4

from aethon.distributed_worker import DistributedWorker
from aethon.schemas import Task, TaskStatus


class FakeStore:
    def __init__(self):
        self.calls = []
        self.rows = []

    def execute(self, query, params=()):
        self.calls.append((query, params))
        if query.startswith("UPDATE tasks"):
            return [(params[3],)] if "worker_leases" in query else []
        return self.rows


class FakePersistence:
    def __init__(self, claimed=None):
        self.claimed = claimed
        self.store = FakeStore()
        self.released = []

    def claim_next_task(self, worker_id, lease_seconds):
        value, self.claimed = self.claimed, None
        return value

    def release_lease(self, task_id, worker_id, token):
        self.released.append((task_id, worker_id, token))
        return True

    def claim_expired(self, worker_id, lease_seconds):
        return []


def test_worker_poll_once_claims_and_completes_exactly_one_task():
    from aethon.distributed_persistence import ClaimedTask
    task_id = uuid4()
    claimed = ClaimedTask(task_id, "do work", None, "owner", 5, "QUEUED", "token")
    persistence = FakePersistence(claimed)
    worker = DistributedWorker(persistence, worker_id="worker-1")
    worker.runtime.run = lambda task: Task(task_id=task.task_id, goal=task.goal, project_id=task.project_id,
                                            owner_id=task.owner_id, priority=task.priority,
                                            status=TaskStatus.SUCCEEDED, result={"ok": True})
    result = worker.poll_once()
    assert result is not None
    assert result.task_id == task_id
    assert result.status == "SUCCEEDED"
    assert persistence.released == [(task_id, "worker-1", "token")]


def test_worker_idle_when_queue_is_empty():
    worker = DistributedWorker(FakePersistence(None), worker_id="worker-1")
    assert worker.poll_once() is None

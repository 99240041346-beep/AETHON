from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from uuid import UUID

from .agent import AgentRuntime
from .distributed_persistence import ClaimedTask, DistributedTaskPersistence
from .schemas import Task, TaskStatus


@dataclass(frozen=True)
class WorkerResult:
    task_id: UUID
    status: str
    error: str | None = None


class DistributedWorker:
    """Polls the shared durable queue and executes only atomically claimed work."""

    def __init__(self, persistence: DistributedTaskPersistence, runtime: AgentRuntime | None = None,
                 worker_id: str | None = None, lease_seconds: float | None = None,
                 poll_seconds: float | None = None):
        self.persistence = persistence
        self.runtime = runtime or AgentRuntime()
        self.worker_id = worker_id or os.getenv("AETHON_WORKER_ID") or f"worker-{os.getpid()}"
        self.lease_seconds = lease_seconds or float(os.getenv("AETHON_WORKER_LEASE_SECONDS", "30"))
        self.poll_seconds = poll_seconds or float(os.getenv("AETHON_WORKER_POLL_SECONDS", "0.5"))
        if self.lease_seconds <= 0 or self.poll_seconds <= 0:
            raise ValueError("worker timing values must be > 0")
        self._stop = threading.Event()

    def claim(self) -> ClaimedTask | None:
        return self.persistence.claim_next_task(self.worker_id, self.lease_seconds)

    def execute_claim(self, claimed: ClaimedTask) -> WorkerResult:
        task = Task(task_id=claimed.task_id, goal=claimed.goal, project_id=claimed.project_id,
                    owner_id=claimed.owner_id, priority=claimed.priority, status=TaskStatus.QUEUED)
        try:
            result = self.runtime.run(task)
            self._persist_result(result, claimed.lease_token)
            self.persistence.release_lease(claimed.task_id, self.worker_id, claimed.lease_token)
            return WorkerResult(claimed.task_id, result.status.value, result.error)
        except BaseException as exc:
            self._mark_failed(claimed, exc)
            return WorkerResult(claimed.task_id, TaskStatus.FAILED.value, str(exc))

    def poll_once(self) -> WorkerResult | None:
        claimed = self.claim()
        if claimed is None:
            return None
        return self.execute_claim(claimed)

    def recover_expired(self) -> int:
        return len(self.persistence.claim_expired(self.worker_id, self.lease_seconds))

    def run_forever(self) -> None:
        while not self._stop.is_set():
            result = self.poll_once()
            if result is None:
                self._stop.wait(self.poll_seconds)

    def stop(self) -> None:
        self._stop.set()

    def _persist_result(self, result: Task, lease_token: str) -> None:
        rows = self.persistence.store.execute(
            """UPDATE tasks SET status=%s,result_json=%s::jsonb,error=%s,updated_at=NOW()
               WHERE task_id=%s AND EXISTS (
                 SELECT 1 FROM worker_leases WHERE task_id=%s AND worker_id=%s AND lease_token=%s
               ) RETURNING task_id""",
            (result.status.value, json.dumps(result.result), result.error, str(result.task_id),
             str(result.task_id), self.worker_id, lease_token),
        )
        if not rows:
            raise RuntimeError("task lease was lost before completion")

    def _mark_failed(self, claimed: ClaimedTask, exc: BaseException) -> None:
        self.persistence.store.execute(
            """UPDATE tasks SET status='FAILED',error=%s,updated_at=NOW()
               WHERE task_id=%s AND EXISTS (
                 SELECT 1 FROM worker_leases WHERE task_id=%s AND worker_id=%s AND lease_token=%s
               )""",
            (str(exc), str(claimed.task_id), str(claimed.task_id), self.worker_id, claimed.lease_token),
        )
        self.persistence.release_lease(claimed.task_id, self.worker_id, claimed.lease_token)

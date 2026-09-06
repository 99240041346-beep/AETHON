from __future__ import annotations

import threading
from typing import Callable, Generic, TypeVar

from .worker_lease import WorkerLeaseStore

T = TypeVar("T")
R = TypeVar("R")


class LeasedWorkerPool(Generic[T, R]):
    """Runs work only while holding a renewable durable worker lease."""

    def __init__(self, worker: Callable[[T], R], leases: WorkerLeaseStore, worker_id: str, lease_seconds: float = 30.0, heartbeat_seconds: float = 5.0):
        if lease_seconds <= 0 or heartbeat_seconds <= 0 or heartbeat_seconds >= lease_seconds:
            raise ValueError("heartbeat_seconds must be positive and less than lease_seconds")
        self._worker = worker
        self._leases = leases
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds

    def run(self, task_id: str, task: T) -> R:
        token = self._leases.acquire(task_id, self.worker_id, self.lease_seconds)
        stop = threading.Event()
        lease_lost = threading.Event()

        def heartbeat() -> None:
            while not stop.wait(self.heartbeat_seconds):
                if not self._leases.heartbeat(task_id, self.worker_id, token, self.lease_seconds):
                    lease_lost.set()
                    return

        thread = threading.Thread(target=heartbeat, name=f"aethon-heartbeat-{self.worker_id}", daemon=True)
        thread.start()
        try:
            result = self._worker(task)
            if lease_lost.is_set():
                raise RuntimeError("worker lease was lost during execution")
            return result
        finally:
            stop.set()
            thread.join(timeout=self.heartbeat_seconds)
            self._leases.release(task_id, self.worker_id, token)

    def lease_is_current(self, task_id: str, token: str) -> bool:
        record = self._leases.get(task_id)
        return bool(record and not record["expired"] and record["worker_id"] == self.worker_id and record["lease_token"] == token)

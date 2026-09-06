from __future__ import annotations

import threading
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .worker_lease import WorkerLeaseStore

T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True)
class WorkerExecution(Generic[T, R]):
    worker_id: str
    task: T
    future: Future


class LeasedWorkerPool(Generic[T, R]):
    """Executes scheduler work only while holding a renewable worker lease."""

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

        def heartbeat() -> None:
            while not stop.wait(self.heartbeat_seconds):
                if not self._leases.heartbeat(task_id, self.worker_id, token, self.lease_seconds):
                    stop.set()
                    return

        thread = threading.Thread(target=heartbeat, name=f"aethon-heartbeat-{self.worker_id}", daemon=True)
        thread.start()
        try:
            return self._worker(task)
        finally:
            stop.set()
            thread.join(timeout=self.heartbeat_seconds)
            self._leases.release(task_id, self.worker_id, token)

    def lease_is_current(self, task_id: str, token: str) -> bool:
        lease = self._leases.get(task_id)
        return bool(lease and lease["worker_id"] == self.worker_id and lease["lease_token"] == token and not lease["expired"])

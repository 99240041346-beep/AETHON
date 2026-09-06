from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from app.worker_lease import WorkerLeaseStore

T = TypeVar("T")


@dataclass(frozen=True)
class RecoveryResult:
    expired_leases: int
    recovered_tasks: int
    skipped_tasks: int


class WorkerRecoveryCoordinator(Generic[T]):
    """Re-admits work whose worker lease has expired, without duplicating live work."""

    def __init__(
        self,
        leases: WorkerLeaseStore,
        list_recoverable: Callable[[], list[T]],
        task_id: Callable[[T], str],
        submit: Callable[[T], object],
    ):
        self.leases = leases
        self.list_recoverable = list_recoverable
        self.task_id = task_id
        self.submit = submit

    def recover_once(self) -> RecoveryResult:
        expired = self.leases.recover_expired()
        recovered = 0
        skipped = 0
        for task in self.list_recoverable():
            lease = self.leases.get(self.task_id(task))
            if lease is not None and not bool(lease["expired"]):
                skipped += 1
                continue
            self.submit(task)
            recovered += 1
        return RecoveryResult(expired_leases=expired, recovered_tasks=recovered, skipped_tasks=skipped)

    def recover_with_retry(self, attempts: int = 1, delay_seconds: float = 0.0) -> RecoveryResult:
        if attempts < 1:
            raise ValueError("attempts must be >= 1")
        result = RecoveryResult(0, 0, 0)
        for index in range(attempts):
            result = self.recover_once()
            if result.recovered_tasks or index == attempts - 1:
                return result
            if delay_seconds > 0:
                time.sleep(delay_seconds)
        return result


__all__ = ["RecoveryResult", "WorkerRecoveryCoordinator"]

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from .worker_lease import WorkerLeaseStore

T = TypeVar("T")


@dataclass(frozen=True)
class RecoveryResult:
    expired_leases: int
    recovered_tasks: int
    skipped_tasks: int


class WorkerRecoveryCoordinator(Generic[T]):
    """Re-admits durable work whose previous worker lease has expired.

    The coordinator intentionally delegates task discovery and submission to
    injected callbacks so it can work with SQLite today and a shared database
    task store later without changing recovery semantics.
    """

    def __init__(
        self,
        leases: WorkerLeaseStore,
        list_recoverable: Callable[[], list[T]],
        task_id: Callable[[T], str],
        submit: Callable[[T], object],
    ):
        self._leases = leases
        self._list_recoverable = list_recoverable
        self._task_id = task_id
        self._submit = submit

    def recover_once(self) -> RecoveryResult:
        expired = self._leases.recover_expired()
        recovered = 0
        skipped = 0
        for task in self._list_recoverable():
            task_key = self._task_id(task)
            if self._leases.get(task_key) is not None:
                skipped += 1
                continue
            self._submit(task)
            recovered += 1
        return RecoveryResult(expired, recovered, skipped)

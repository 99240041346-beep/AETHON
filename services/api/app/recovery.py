from __future__ import annotations

from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from .distributed_persistence import DistributedTaskPersistence


@dataclass(frozen=True)
class RecoveryReport:
    inspected: int
    recoverable: tuple[UUID, ...]
    claimed: tuple[UUID, ...] = ()


class WorkerRecoveryCoordinator:
    """Find and atomically claim tasks abandoned by expired workers."""

    def __init__(self, persistence: DistributedTaskPersistence):
        self.persistence = persistence

    def scan(self) -> RecoveryReport:
        tasks = self.persistence.recoverable_tasks()
        return RecoveryReport(inspected=len(tasks), recoverable=tuple(tasks))

    def recover(
        self,
        worker_id: str | None = None,
        admit: Callable[[UUID], None] | None = None,
        lease_seconds: float = 30.0,
    ) -> RecoveryReport:
        """Atomically claim expired leases and optionally re-admit claimed tasks.

        Claiming is done by the shared persistence layer, so two workers racing
        to recover the same task cannot both obtain the lease.  ``admit`` is
        deliberately invoked only after the lease is owned by this worker.
        """
        if not worker_id:
            return self.scan()
        claimed_candidates = self.persistence.claim_expired(worker_id, lease_seconds)
        claimed = tuple(candidate.task_id for candidate in claimed_candidates)
        if admit is not None:
            for task_id in claimed:
                admit(task_id)
        remaining = self.persistence.recoverable_tasks()
        inspected = len(set(remaining).union(claimed))
        return RecoveryReport(inspected=inspected, recoverable=tuple(remaining), claimed=claimed)

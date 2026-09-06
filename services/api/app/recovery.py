from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .distributed_persistence import DistributedTaskPersistence


@dataclass(frozen=True)
class RecoveryReport:
    inspected: int
    recoverable: tuple[UUID, ...]


class WorkerRecoveryCoordinator:
    """Finds durable tasks abandoned by expired workers."""

    def __init__(self, persistence: DistributedTaskPersistence):
        self.persistence = persistence

    def scan(self) -> RecoveryReport:
        tasks = self.persistence.recoverable_tasks()
        return RecoveryReport(inspected=len(tasks), recoverable=tuple(tasks))

    def recover(self) -> RecoveryReport:
        """Return recovery candidates; execution is re-admitted by the scheduler."""
        return self.scan()

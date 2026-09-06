from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from .distributed_persistence import DistributedTaskPersistence


@dataclass(frozen=True)
class CompletionResult:
    applied: bool
    already_completed: bool = False


class ExecutionGuard:
    """Fenced, idempotent task completion/failure operations."""

    def __init__(self, persistence: DistributedTaskPersistence):
        self.persistence = persistence

    def complete(self, task_id: UUID | str, worker_id: str, lease_token: str, result_json: str) -> CompletionResult:
        rows = self.persistence.store.execute(
            """UPDATE tasks SET status='SUCCEEDED', result_json=%s::jsonb, error=NULL, updated_at=NOW()
               WHERE task_id=%s AND status <> 'SUCCEEDED'
                 AND EXISTS (SELECT 1 FROM worker_leases WHERE task_id=%s AND worker_id=%s AND lease_token=%s AND expires_at > NOW())
               RETURNING task_id""",
            (result_json, str(task_id), str(task_id), worker_id, lease_token),
        )
        if rows:
            self.persistence.release_lease(task_id, worker_id, lease_token)
            return CompletionResult(True)
        state = self.persistence.store.execute("SELECT status FROM tasks WHERE task_id=%s", (str(task_id),))
        if state and state[0][0] == 'SUCCEEDED':
            return CompletionResult(False, True)
        return CompletionResult(False)

    def fail(self, task_id: UUID | str, worker_id: str, lease_token: str, error: str) -> bool:
        rows = self.persistence.store.execute(
            """UPDATE tasks SET status='FAILED', error=%s, updated_at=NOW()
               WHERE task_id=%s AND status <> 'SUCCEEDED'
                 AND EXISTS (SELECT 1 FROM worker_leases WHERE task_id=%s AND worker_id=%s AND lease_token=%s AND expires_at > NOW())
               RETURNING task_id""",
            (error, str(task_id), str(task_id), worker_id, lease_token),
        )
        if rows:
            self.persistence.release_lease(task_id, worker_id, lease_token)
            return True
        return False

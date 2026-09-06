from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from .postgres import PostgresStore, PostgresStoreUnavailable


@dataclass(frozen=True)
class RecoveryCandidate:
    task_id: UUID
    worker_id: str
    lease_token: str
    expired_at: datetime


class DistributedTaskPersistence:
    """Shared PostgreSQL persistence primitives for worker recovery."""

    def __init__(self, database_url: str | None = None):
        self.store = PostgresStore(database_url)

    def ensure_schema(self) -> None:
        self.store.execute(
            """CREATE TABLE IF NOT EXISTS worker_leases (
                task_id UUID PRIMARY KEY REFERENCES tasks(task_id) ON DELETE CASCADE,
                worker_id TEXT NOT NULL,
                lease_token TEXT NOT NULL,
                acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_worker_leases_expires ON worker_leases(expires_at);
            CREATE INDEX IF NOT EXISTS idx_tasks_recovery ON tasks(status, updated_at);"""
        )

    def claim_expired(self, worker_id: str, lease_seconds: float = 30.0) -> list[RecoveryCandidate]:
        if not worker_id:
            raise ValueError("worker_id is required")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        rows = self.store.execute(
            """DELETE FROM worker_leases
               WHERE expires_at <= NOW()
               RETURNING task_id, worker_id, lease_token, expires_at"""
        )
        return [
            RecoveryCandidate(UUID(row[0]), row[1], row[2], row[3])
            for row in rows
        ]

    def recoverable_tasks(self) -> list[UUID]:
        rows = self.store.execute(
            """SELECT t.task_id FROM tasks t
               LEFT JOIN worker_leases l ON l.task_id = t.task_id
               WHERE t.status IN ('QUEUED','EXECUTING','REPLANNING','VERIFYING','AWAITING_APPROVAL')
                 AND (l.task_id IS NULL OR l.expires_at <= NOW())
               ORDER BY t.priority ASC, t.created_at ASC"""
        )
        return [UUID(row[0]) for row in rows]

    @staticmethod
    def configured() -> bool:
        value = os.getenv("AETHON_DATABASE_URL", "")
        return value.startswith(("postgres://", "postgresql://"))

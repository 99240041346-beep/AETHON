from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
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

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise PostgresStoreUnavailable("psycopg is not installed") from exc
        return psycopg.connect(self.store.database_url, connect_timeout=5)

    def acquire_lease(self, task_id: UUID | str, worker_id: str, lease_seconds: float = 30.0) -> str | None:
        """Atomically acquire a lease only when no live lease exists."""
        if not worker_id:
            raise ValueError("worker_id is required")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        token = uuid.uuid4().hex
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO worker_leases
                       (task_id, worker_id, lease_token, acquired_at, heartbeat_at, expires_at)
                       VALUES (%s, %s, %s, NOW(), NOW(), NOW() + (%s * INTERVAL '1 second'))
                       ON CONFLICT (task_id) DO UPDATE
                       SET worker_id = EXCLUDED.worker_id,
                           lease_token = EXCLUDED.lease_token,
                           acquired_at = EXCLUDED.acquired_at,
                           heartbeat_at = EXCLUDED.heartbeat_at,
                           expires_at = EXCLUDED.expires_at
                       WHERE worker_leases.expires_at <= NOW()
                       RETURNING lease_token""",
                    (str(task_id), worker_id, token, lease_seconds),
                )
                row = cur.fetchone()
                return row[0] if row else None

    def heartbeat_lease(self, task_id: UUID | str, worker_id: str, lease_token: str, lease_seconds: float = 30.0) -> bool:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        rows = self.store.execute(
            """UPDATE worker_leases
               SET heartbeat_at=NOW(), expires_at=NOW() + (%s * INTERVAL '1 second')
               WHERE task_id=%s AND worker_id=%s AND lease_token=%s AND expires_at > NOW()
               RETURNING task_id""",
            (lease_seconds, str(task_id), worker_id, lease_token),
        )
        return bool(rows)

    def release_lease(self, task_id: UUID | str, worker_id: str, lease_token: str) -> bool:
        rows = self.store.execute(
            "DELETE FROM worker_leases WHERE task_id=%s AND worker_id=%s AND lease_token=%s RETURNING task_id",
            (str(task_id), worker_id, lease_token),
        )
        return bool(rows)

    def claim_expired(self, worker_id: str, lease_seconds: float = 30.0) -> list[RecoveryCandidate]:
        """Claim expired leases atomically; racing workers can only have one winner."""
        if not worker_id:
            raise ValueError("worker_id is required")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        claimed: list[RecoveryCandidate] = []
        rows = self.store.execute(
            """SELECT task_id, worker_id, lease_token, expires_at
               FROM worker_leases
               WHERE expires_at <= NOW()
               ORDER BY expires_at ASC"""
        )
        for task_id, previous_worker, previous_token, expired_at in rows:
            token = self.acquire_lease(task_id, worker_id, lease_seconds)
            if token:
                claimed.append(RecoveryCandidate(UUID(str(task_id)), previous_worker, previous_token, expired_at))
        return claimed

    def recoverable_tasks(self) -> list[UUID]:
        """Return abandoned executable tasks; approval-paused work is excluded."""
        rows = self.store.execute(
            """SELECT t.task_id FROM tasks t
               LEFT JOIN worker_leases l ON l.task_id = t.task_id
               WHERE t.status IN ('QUEUED','EXECUTING','REPLANNING','VERIFYING')
                 AND (l.task_id IS NULL OR l.expires_at <= NOW())
               ORDER BY t.priority ASC, t.created_at ASC"""
        )
        return [UUID(str(row[0])) for row in rows]

    @staticmethod
    def configured() -> bool:
        value = os.getenv("AETHON_DATABASE_URL", "")
        return value.startswith(("postgres://", "postgresql://"))

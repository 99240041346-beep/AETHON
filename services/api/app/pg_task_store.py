from __future__ import annotations

import json
import uuid
from typing import Any
from uuid import UUID

from .postgres import PostgresStore, PostgresStoreUnavailable
from .schemas import Task, TaskStatus


class PostgreSQLTaskStore:
    """Shared PostgreSQL task/event persistence for multi-worker deployments.

    SQLite remains the local-development default. This store is selected explicitly
    by callers so a missing production database never silently falls back to a
    process-local database.
    """

    def __init__(self, database_url: str | None = None):
        self.store = PostgresStore(database_url)

    def ensure_schema(self) -> None:
        self.store.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                task_id UUID PRIMARY KEY,
                goal TEXT NOT NULL,
                project_id TEXT,
                owner_id TEXT NOT NULL DEFAULT 'local-dev',
                priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 10),
                status TEXT NOT NULL,
                result_json JSONB,
                error TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_queue ON tasks(status, priority, created_at);
            CREATE TABLE IF NOT EXISTS events (
                event_id UUID PRIMARY KEY,
                task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_events_task_created ON events(task_id, created_at);
            CREATE TABLE IF NOT EXISTS worker_leases (
                task_id UUID PRIMARY KEY REFERENCES tasks(task_id) ON DELETE CASCADE,
                worker_id TEXT NOT NULL,
                lease_token TEXT NOT NULL,
                acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_worker_leases_expires ON worker_leases(expires_at);"""
        )

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise PostgresStoreUnavailable("psycopg is not installed") from exc
        return psycopg.connect(self.store.database_url, connect_timeout=5)

    @staticmethod
    def _task(row: tuple[Any, ...]) -> Task:
        return Task(
            task_id=UUID(str(row[0])), goal=row[1], project_id=row[2], owner_id=row[3],
            priority=row[4], status=TaskStatus(row[5]),
            result=row[6], error=row[7],
        )

    def put_task(self, task: Task) -> Task:
        rows = self.store.execute(
            """INSERT INTO tasks(task_id, goal, project_id, owner_id, priority, status, result_json, error)
               VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
               ON CONFLICT(task_id) DO UPDATE SET goal=EXCLUDED.goal,
                 project_id=EXCLUDED.project_id, owner_id=EXCLUDED.owner_id,
                 priority=EXCLUDED.priority, status=EXCLUDED.status,
                 result_json=EXCLUDED.result_json, error=EXCLUDED.error,
                 updated_at=NOW()
               RETURNING task_id, goal, project_id, owner_id, priority, status, result_json, error""",
            (str(task.task_id), task.goal, task.project_id, task.owner_id, task.priority,
             task.status.value, json.dumps(task.result), task.error),
        )
        return self._task(rows[0])

    def get_task(self, task_id: UUID | str) -> Task | None:
        rows = self.store.execute(
            """SELECT task_id, goal, project_id, owner_id, priority, status, result_json, error
               FROM tasks WHERE task_id=%s""", (str(task_id),)
        )
        return self._task(rows[0]) if rows else None

    def claim_task(self, worker_id: str, lease_seconds: float = 30.0) -> tuple[Task, str] | None:
        """Atomically select one queued task and create its worker lease.

        PostgreSQL row locking makes competing workers mutually exclusive. The
        lease and status transition commit together, preventing a worker from
        observing a claimed task without its lease.
        """
        if not worker_id:
            raise ValueError("worker_id is required")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        token = uuid.uuid4().hex
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT task_id FROM tasks
                       WHERE status='QUEUED'
                       ORDER BY priority ASC, created_at ASC
                       FOR UPDATE SKIP LOCKED LIMIT 1"""
                )
                row = cur.fetchone()
                if row is None:
                    return None
                task_id = row[0]
                cur.execute(
                    """INSERT INTO worker_leases(task_id, worker_id, lease_token, acquired_at, heartbeat_at, expires_at)
                       VALUES (%s,%s,%s,NOW(),NOW(),NOW() + (%s * INTERVAL '1 second'))
                       ON CONFLICT (task_id) DO UPDATE
                       SET worker_id=EXCLUDED.worker_id, lease_token=EXCLUDED.lease_token,
                           acquired_at=EXCLUDED.acquired_at, heartbeat_at=EXCLUDED.heartbeat_at,
                           expires_at=EXCLUDED.expires_at
                       WHERE worker_leases.expires_at <= NOW()
                       RETURNING task_id""",
                    (str(task_id), worker_id, token, lease_seconds),
                )
                if cur.fetchone() is None:
                    return None
                cur.execute(
                    """UPDATE tasks SET status='EXECUTING', updated_at=NOW()
                       WHERE task_id=%s
                       RETURNING task_id, goal, project_id, owner_id, priority, status, result_json, error""",
                    (str(task_id),),
                )
                task = self._task(cur.fetchone())
                return task, token

    def heartbeat(self, task_id: UUID | str, worker_id: str, lease_token: str, lease_seconds: float = 30.0) -> bool:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be > 0")
        rows = self.store.execute(
            """UPDATE worker_leases SET heartbeat_at=NOW(), expires_at=NOW() + (%s * INTERVAL '1 second')
               WHERE task_id=%s AND worker_id=%s AND lease_token=%s AND expires_at > NOW()
               RETURNING task_id""",
            (lease_seconds, str(task_id), worker_id, lease_token),
        )
        return bool(rows)

    def release(self, task_id: UUID | str, worker_id: str, lease_token: str) -> bool:
        rows = self.store.execute(
            "DELETE FROM worker_leases WHERE task_id=%s AND worker_id=%s AND lease_token=%s RETURNING task_id",
            (str(task_id), worker_id, lease_token),
        )
        return bool(rows)

    def recoverable_tasks(self) -> list[UUID]:
        rows = self.store.execute(
            """SELECT t.task_id FROM tasks t
               LEFT JOIN worker_leases l ON l.task_id=t.task_id
               WHERE t.status IN ('QUEUED','EXECUTING','REPLANNING','VERIFYING')
                 AND (l.task_id IS NULL OR l.expires_at <= NOW())
               ORDER BY t.priority ASC, t.created_at ASC"""
        )
        return [UUID(str(row[0])) for row in rows]

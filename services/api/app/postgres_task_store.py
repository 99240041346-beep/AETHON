from __future__ import annotations

import json
import os
import socket
import threading
from concurrent.futures import Future
from datetime import datetime, timezone
from uuid import UUID

from aethon.agent import AgentRuntime
from aethon.agent_state import AgentStateStore
from aethon.distributed_persistence import DistributedTaskPersistence
from aethon.scheduler import TaskScheduler
from aethon.schemas import Event, Task, TaskCreate, TaskStatus
from aethon.worker_pool import LeasedWorkerPool
from aethon.worker_lease import WorkerLeaseStore
from aethon.postgres import PostgresStore


class PostgreSQLTaskStore:
    """Shared PostgreSQL task store used when AETHON_DATABASE_URL is configured."""

    def __init__(self, database_url: str | None = None):
        self.postgres = PostgresStore(database_url)
        self.database_url = self.postgres.database_url
        self.worker_id = os.getenv("AETHON_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
        self.state_store = AgentStateStore(os.getenv("AETHON_AGENT_STATE_PATH", ".aethon/agent_state.db"))
        self.runtime = AgentRuntime(state_store=self.state_store)
        # The distributed lease table is authoritative for PostgreSQL workers.
        self.distributed = DistributedTaskPersistence(self.database_url)
        self.distributed.ensure_schema()
        self.lease_store = None
        self.worker_pool = LeasedWorkerPool(
            self.runtime.run,
            _PostgresLeaseAdapter(self.distributed),
            self.worker_id,
            lease_seconds=float(os.getenv("AETHON_WORKER_LEASE_SECONDS", "30")),
            heartbeat_seconds=float(os.getenv("AETHON_WORKER_HEARTBEAT_SECONDS", "5")),
        )
        self.scheduler = TaskScheduler(self.runtime.run, worker_pool=self.worker_pool, lease_key=lambda task: str(task.task_id))
        self._futures: dict[UUID, Future] = {}
        self._future_lock = threading.Lock()
        self._init_db()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url, connect_timeout=5)

    def _init_db(self) -> None:
        self.postgres.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id UUID PRIMARY KEY,
            goal TEXT NOT NULL,
            project_id TEXT,
            owner_id TEXT NOT NULL DEFAULT 'local-dev',
            priority INTEGER NOT NULL DEFAULT 5,
            status TEXT NOT NULL,
            result_json JSONB,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id UUID PRIMARY KEY,
            task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            data_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id UUID PRIMARY KEY,
            task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
            action TEXT NOT NULL,
            data_json JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_recovery ON tasks(status, priority, created_at);
        """)

    def _persist_task(self, task: Task) -> None:
        self.postgres.execute("""
        INSERT INTO tasks(task_id,goal,project_id,owner_id,priority,status,result_json,error,created_at,updated_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,NOW(),NOW())
        ON CONFLICT(task_id) DO UPDATE SET goal=EXCLUDED.goal, project_id=EXCLUDED.project_id,
        owner_id=EXCLUDED.owner_id, priority=EXCLUDED.priority, status=EXCLUDED.status,
        result_json=EXCLUDED.result_json, error=EXCLUDED.error, updated_at=NOW()
        """, (str(task.task_id), task.goal, task.project_id, task.owner_id, task.priority,
              task.status.value, json.dumps(task.result), task.error))

    def _persist_events(self, task_id: UUID) -> None:
        events = self.runtime.events.get(task_id, [])
        for event in events:
            self.postgres.execute("""
            INSERT INTO events(event_id,task_id,type,data_json,created_at)
            VALUES(%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(event_id) DO NOTHING
            """, (str(event.event_id), str(event.task_id), event.type, json.dumps(event.data)))
            if event.type.startswith("audit."):
                self.postgres.execute("""
                INSERT INTO audit_log(audit_id,task_id,action,data_json,created_at)
                VALUES(%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(audit_id) DO NOTHING
                """, (str(event.event_id), str(event.task_id), event.type[6:], json.dumps(event.data)))

    def _submit(self, task: Task) -> Future:
        future = self.scheduler.submit(task, priority=task.priority)
        with self._future_lock:
            self._futures[task.task_id] = future
        return future

    def _forget_future(self, task_id: UUID) -> None:
        with self._future_lock:
            self._futures.pop(task_id, None)

    def create(self, request: TaskCreate) -> Task:
        task = Task(goal=request.goal, project_id=request.project_id, priority=request.priority, owner_id=request.owner_id)
        self._persist_task(task)
        self.runtime._event(task, "task.queued", {"priority": task.priority, "scheduler": "bounded-thread-pool", "worker_id": self.worker_id})
        self._persist_events(task.task_id)
        future = self._submit(task)
        try:
            result = future.result()
        finally:
            self._forget_future(task.task_id)
        self._persist_task(result)
        self._persist_events(result.task_id)
        return result

    def get(self, task_id: UUID) -> Task | None:
        rows = self.postgres.execute("SELECT task_id,goal,project_id,priority,owner_id,status,result_json,error FROM tasks WHERE task_id=%s", (str(task_id),))
        if not rows:
            return None
        row = rows[0]
        result = row[6]
        if isinstance(result, str):
            result = json.loads(result)
        return Task(task_id=UUID(str(row[0])), goal=row[1], project_id=row[2], priority=row[3], owner_id=row[4], status=row[5], result=result, error=row[7])

    def events(self, task_id: UUID) -> list[Event]:
        rows = self.postgres.execute("SELECT event_id,task_id,type,data_json FROM events WHERE task_id=%s ORDER BY created_at", (str(task_id),))
        return [Event(event_id=UUID(str(r[0])), task_id=UUID(str(r[1])), type=r[2], data=r[3] if isinstance(r[3], dict) else json.loads(r[3])) for r in rows]

    def audit(self, task_id: UUID | None = None) -> list[dict]:
        if task_id is None:
            rows = self.postgres.execute("SELECT audit_id,task_id,action,data_json,created_at FROM audit_log ORDER BY created_at")
        else:
            rows = self.postgres.execute("SELECT audit_id,task_id,action,data_json,created_at FROM audit_log WHERE task_id=%s ORDER BY created_at", (str(task_id),))
        return [{"audit_id": str(r[0]), "task_id": str(r[1]) if r[1] else None, "action": r[2], "data": r[3] if isinstance(r[3], dict) else json.loads(r[3]), "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4])} for r in rows]

    def scheduler_status(self) -> dict[str, object]:
        snapshot = self.scheduler.snapshot()
        snapshot["worker_id"] = self.worker_id
        snapshot["persistence"] = "postgresql"
        return snapshot

    def _lease_is_live(self, task_id: UUID) -> bool:
        rows = self.postgres.execute("SELECT 1 FROM worker_leases WHERE task_id=%s AND expires_at > NOW()", (str(task_id),))
        return bool(rows)

    def pause(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None: return None
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}: raise ValueError("task is already terminal")
        self.state_store.request_pause(task_id)
        task.status = TaskStatus.PAUSED
        self._persist_task(task)
        self.runtime._event(task, "task.pause_requested", {"task_id": str(task_id)})
        self._persist_events(task_id)
        return task

    def resume(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None: return None
        if task.status != TaskStatus.PAUSED: raise ValueError("task is not paused")
        if self.state_store.load(task_id) is None: raise ValueError("no persisted agent state exists for task")
        self.state_store.clear_pause(task_id)
        task.error = None
        future = self._submit(task)
        try: result = future.result()
        finally: self._forget_future(task.task_id)
        self._persist_task(result); self._persist_events(result.task_id)
        return result

    def cancel(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None: return None
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}: return task
        self.state_store.request_cancel(task_id)
        with self._future_lock: future = self._futures.get(task_id)
        if future is not None and future.cancel(): self.runtime._event(task, "task.cancelled", {"queued": True})
        else: self.runtime._event(task, "task.cancel_requested", {"running": True})
        task.status = TaskStatus.CANCELLED
        self._persist_task(task); self._persist_events(task_id)
        return task


class _PostgresLeaseAdapter:
    def __init__(self, persistence: DistributedTaskPersistence): self.persistence = persistence
    def acquire(self, task_id: str, worker_id: str, lease_seconds: float):
        token = self.persistence.acquire_lease(task_id, worker_id, lease_seconds)
        if token is None:
            raise RuntimeError("task is already leased by another worker")
        return token
    def heartbeat(self, task_id: str, worker_id: str, token: str, lease_seconds: float):
        return self.persistence.heartbeat_lease(task_id, worker_id, token, lease_seconds)
    def release(self, task_id: str, worker_id: str, token: str):
        return self.persistence.release_lease(task_id, worker_id, token)

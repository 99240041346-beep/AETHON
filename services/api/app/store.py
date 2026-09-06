from __future__ import annotations

import json
import os
import socket
import sqlite3
import threading
from concurrent.futures import Future
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from aethon.agent import AgentRuntime
from aethon.agent_state import AgentStateStore
from aethon.scheduler import TaskScheduler
from aethon.schemas import Event, Task, TaskCreate, TaskStatus
from aethon.worker_lease import WorkerLeaseStore
from aethon.worker_pool import LeasedWorkerPool


class TaskStore:
    """Durable task/event store with bounded, lease-protected agent scheduling."""

    def __init__(self, database_path: str | None = None):
        path = database_path or os.getenv("AETHON_SQLITE_PATH", ".aethon/aethon.db")
        self.database_path = Path(path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_store = AgentStateStore(str(self.database_path.with_name(self.database_path.stem + "_agent_state.db")))
        self.runtime = AgentRuntime(state_store=self.state_store)
        self.worker_id = os.getenv("AETHON_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
        lease_path = os.getenv("AETHON_LEASE_PATH", str(self.database_path.with_name(self.database_path.stem + "_worker_leases.db")))
        self.lease_store = WorkerLeaseStore(lease_path)
        self.worker_pool = LeasedWorkerPool(
            self.runtime.run,
            self.lease_store,
            self.worker_id,
            lease_seconds=float(os.getenv("AETHON_WORKER_LEASE_SECONDS", "30")),
            heartbeat_seconds=float(os.getenv("AETHON_WORKER_HEARTBEAT_SECONDS", "5")),
        )
        self.scheduler = TaskScheduler(self.runtime.run, worker_pool=self.worker_pool, lease_key=lambda task: str(task.task_id))
        self._futures: dict[UUID, Future] = {}
        self._future_lock = threading.Lock()
        self._init_db()
        self._recover_tasks()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, goal TEXT NOT NULL, project_id TEXT,
                priority INTEGER NOT NULL, owner_id TEXT NOT NULL DEFAULT 'local-dev', status TEXT NOT NULL,
                result_json TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, type TEXT NOT NULL,
                data_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id, created_at);
            CREATE TABLE IF NOT EXISTS audit_log (
                audit_id TEXT PRIMARY KEY, task_id TEXT, action TEXT NOT NULL,
                data_json TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id, created_at);
            """)
            columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            if "owner_id" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local-dev'")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _persist_task(self, task: Task) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO tasks(task_id,goal,project_id,priority,owner_id,status,result_json,error,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET goal=excluded.goal,
                   project_id=excluded.project_id, priority=excluded.priority, owner_id=excluded.owner_id,
                   status=excluded.status, result_json=excluded.result_json, error=excluded.error, updated_at=excluded.updated_at""",
                (str(task.task_id), task.goal, task.project_id, task.priority, task.owner_id, task.status.value,
                 json.dumps(task.result), task.error, now, now),
            )

    def _persist_events(self, task_id: UUID) -> None:
        events = self.runtime.events.get(task_id, [])
        with self._connect() as conn:
            for event in events:
                conn.execute("INSERT OR IGNORE INTO events(event_id,task_id,type,data_json,created_at) VALUES(?,?,?,?,?)",
                    (str(event.event_id), str(event.task_id), event.type, json.dumps(event.data), self._now()))
                if event.type.startswith("audit."):
                    conn.execute("INSERT OR IGNORE INTO audit_log(audit_id,task_id,action,data_json,created_at) VALUES(?,?,?,?,?)",
                        (str(event.event_id), str(event.task_id), event.type[6:], json.dumps(event.data), self._now()))

    def _submit(self, task: Task) -> Future:
        future = self.scheduler.submit(task, priority=task.priority)
        with self._future_lock:
            self._futures[task.task_id] = future
        return future

    def _forget_future(self, task_id: UUID) -> None:
        with self._future_lock:
            self._futures.pop(task_id, None)

    def _recover_tasks(self) -> None:
        """Recover queued work and abandoned active work after restart.

        PAUSED and AWAITING_APPROVAL require explicit user action and are not
        automatically resumed.
        """
        recoverable = {
            TaskStatus.QUEUED.value,
            TaskStatus.PLANNING.value,
            TaskStatus.EXECUTING.value,
            TaskStatus.REPLANNING.value,
            TaskStatus.VERIFYING.value,
        }
        placeholders = ",".join("?" for _ in recoverable)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT task_id, goal, project_id, priority, owner_id, status FROM tasks WHERE status IN ({placeholders}) ORDER BY priority ASC, created_at ASC",
                tuple(recoverable),
            ).fetchall()
        for row in rows:
            task_id = UUID(row["task_id"])
            state = self.state_store.load(task_id)
            if row["status"] != TaskStatus.QUEUED.value and state is None:
                continue
            task = Task(task_id=task_id, goal=row["goal"], project_id=row["project_id"],
                        priority=row["priority"], owner_id=row["owner_id"], status=TaskStatus.QUEUED)
            self._persist_task(task)
            try:
                future = self._submit(task)
            except RuntimeError:
                break
            self.runtime._event(task, "task.recovered", {
                "scheduler": "bounded-thread-pool",
                "worker_id": self.worker_id,
                "resume_from_checkpoint": state is not None,
                "previous_status": row["status"],
                "priority": task.priority,
            })
            self._persist_events(task.task_id)
            future.add_done_callback(lambda completed, task_id=task.task_id: self._persist_recovered_result(task_id, completed))

    def _persist_recovered_result(self, task_id: UUID, future: Future) -> None:
        self._forget_future(task_id)
        try:
            result = future.result()
        except Exception as exc:
            task = self.get(task_id)
            if task is None or task.status in {TaskStatus.CANCELLED, TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED}:
                return
            task.status = TaskStatus.FAILED
            task.error = str(exc)
        else:
            task = result
        self._persist_task(task)
        self._persist_events(task_id)

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

    def scheduler_status(self) -> dict[str, object]:
        snapshot = self.scheduler.snapshot()
        snapshot["worker_id"] = self.worker_id
        return snapshot

    def get(self, task_id: UUID) -> Task | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id=?", (str(task_id),)).fetchone()
        if not row:
            return None
        return Task(task_id=UUID(row["task_id"]), goal=row["goal"], project_id=row["project_id"],
                    priority=row["priority"], owner_id=row["owner_id"], status=row["status"],
                    result=json.loads(row["result_json"]) if row["result_json"] else None, error=row["error"])

    def events(self, task_id: UUID) -> list[Event]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM events WHERE task_id=? ORDER BY created_at", (str(task_id),)).fetchall()
        return [Event(event_id=UUID(r["event_id"]), task_id=UUID(r["task_id"]), type=r["type"], data=json.loads(r["data_json"])) for r in rows]

    def audit(self, task_id: UUID | None = None) -> list[dict]:
        query = "SELECT * FROM audit_log"; args = ()
        if task_id is not None:
            query += " WHERE task_id=?"; args = (str(task_id),)
        query += " ORDER BY created_at"
        with self._connect() as conn:
            rows = conn.execute(query, args).fetchall()
        return [{"audit_id": r["audit_id"], "task_id": r["task_id"], "action": r["action"],
                 "data": json.loads(r["data_json"]), "created_at": r["created_at"]} for r in rows]

    def pause(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}:
            raise ValueError("task is already terminal")
        self.state_store.request_pause(task_id)
        if task.status != TaskStatus.PAUSED:
            task.status = TaskStatus.PAUSED
            self._persist_task(task)
        self.runtime._event(task, "task.pause_requested", {"task_id": str(task_id)})
        self._persist_events(task_id)
        return task

    def resume(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        if task.status != TaskStatus.PAUSED:
            raise ValueError("task is not paused")
        if self.state_store.load(task_id) is None:
            raise ValueError("no persisted agent state exists for task")
        self.state_store.clear_pause(task_id)
        task.error = None
        future = self._submit(task)
        try:
            result = future.result()
        finally:
            self._forget_future(task.task_id)
        self._persist_task(result)
        self._persist_events(result.task_id)
        return result

    def cancel(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}:
            return task
        self.state_store.request_cancel(task_id)
        with self._future_lock:
            future = self._futures.get(task_id)
        if future is not None and future.cancel():
            self.runtime._event(task, "task.cancelled", {"queued": True})
        else:
            self.runtime._event(task, "task.cancel_requested", {"running": True})
        task.status = TaskStatus.CANCELLED
        self._persist_task(task)
        self._persist_events(task_id)
        return task

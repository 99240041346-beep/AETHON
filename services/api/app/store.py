from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from aethon.agent import AgentRuntime
from aethon.agent_state import AgentStateStore
from aethon.schemas import Event, Task, TaskCreate, TaskStatus


class TaskStore:
    """Durable task/event store with SQLite as the AETHON-0 local backend."""

    def __init__(self, database_path: str | None = None):
        path = database_path or os.getenv("AETHON_SQLITE_PATH", ".aethon/aethon.db")
        self.database_path = Path(path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_store = AgentStateStore(str(self.database_path.with_name(self.database_path.stem + "_agent_state.db")))
        self.runtime = AgentRuntime(state_store=self.state_store)
        self._init_db()

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

    def create(self, request: TaskCreate) -> Task:
        task = Task(goal=request.goal, project_id=request.project_id, priority=request.priority, owner_id=request.owner_id)
        self._persist_task(task)
        result = self.runtime.run(task)
        self._persist_task(result)
        self._persist_events(result.task_id)
        return result

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
        result = self.runtime.run(task)
        self._persist_task(result)
        self._persist_events(result.task_id)
        return result

    def cancel(self, task_id: UUID) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        if task.status not in {TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.CANCELLED}:
            task.status = TaskStatus.CANCELLED
            self.state_store.clear_pause(task_id)
            self._persist_task(task)
        return task

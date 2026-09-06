from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class AgentState:
    task_id: str
    plan: dict[str, Any]
    observations: list[str] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    recovery_history: list[dict[str, Any]] = field(default_factory=list)
    last_verified_step: str | None = None
    status: str = "PAUSED"
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentStateStore:
    """Durable task state store with SQLite persistence and in-memory fallback."""

    def __init__(self, path: str = ".aethon/agent_state.db"):
        import os
        import sqlite3

        self._sqlite3 = sqlite3
        self.path = path
        self._memory: dict[str, AgentState] = {}
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            self._conn = sqlite3.connect(path, check_same_thread=False)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS agent_state (task_id TEXT PRIMARY KEY, state_json TEXT NOT NULL, updated_at TEXT NOT NULL)"
            )
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS agent_controls (task_id TEXT PRIMARY KEY, pause_requested INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)"
            )
            self._conn.commit()
        except Exception:
            self._conn = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def save(self, state: AgentState) -> AgentState:
        import json

        state.updated_at = self._now()
        self._memory[state.task_id] = state
        if self._conn is not None:
            self._conn.execute(
                "INSERT INTO agent_state(task_id,state_json,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(task_id) DO UPDATE SET state_json=excluded.state_json, updated_at=excluded.updated_at",
                (state.task_id, json.dumps(asdict(state)), state.updated_at),
            )
            self._conn.commit()
        return state

    def load(self, task_id: UUID | str) -> AgentState | None:
        import json

        key = str(task_id)
        if self._conn is not None:
            row = self._conn.execute("SELECT state_json FROM agent_state WHERE task_id=?", (key,)).fetchone()
            if row:
                data = json.loads(row[0])
                state = AgentState(**data)
                self._memory[key] = state
                return state
        return self._memory.get(key)

    def request_pause(self, task_id: UUID | str) -> None:
        key = str(task_id)
        now = self._now()
        if self._conn is not None:
            self._conn.execute(
                "INSERT INTO agent_controls(task_id,pause_requested,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(task_id) DO UPDATE SET pause_requested=1, updated_at=excluded.updated_at",
                (key, 1, now),
            )
            self._conn.commit()

    def pause_requested(self, task_id: UUID | str) -> bool:
        key = str(task_id)
        if self._conn is not None:
            row = self._conn.execute("SELECT pause_requested FROM agent_controls WHERE task_id=?", (key,)).fetchone()
            return bool(row and row[0])
        return False

    def clear_pause(self, task_id: UUID | str) -> None:
        key = str(task_id)
        if self._conn is not None:
            self._conn.execute("DELETE FROM agent_controls WHERE task_id=?", (key,))
            self._conn.commit()

    def delete(self, task_id: UUID | str) -> None:
        key = str(task_id)
        self._memory.pop(key, None)
        if self._conn is not None:
            self._conn.execute("DELETE FROM agent_state WHERE task_id=?", (key,))
            self._conn.execute("DELETE FROM agent_controls WHERE task_id=?", (key,))
            self._conn.commit()

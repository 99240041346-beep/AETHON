from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


class LeaseConflict(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


class WorkerLeaseStore:
    """Durable task leases preventing duplicate worker ownership."""

    def __init__(self, path: str = ".aethon/worker_leases.db"):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS worker_leases (task_id TEXT PRIMARY KEY, worker_id TEXT NOT NULL, lease_token TEXT NOT NULL, acquired_at TEXT NOT NULL, heartbeat_at TEXT NOT NULL, expires_at REAL NOT NULL)"
        )
        self._conn.commit()

    @staticmethod
    def _now() -> float:
        return datetime.now(timezone.utc).timestamp()

    @staticmethod
    def _iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def acquire(self, task_id: str, worker_id: str, ttl_seconds: float = 30.0) -> str:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        token = uuid.uuid4().hex
        now = self._now()
        with self._lock:
            row = self._conn.execute(
                "SELECT expires_at FROM worker_leases WHERE task_id=?", (task_id,)
            ).fetchone()
            if row and row[0] > now:
                raise LeaseConflict("task is already leased")
            self._conn.execute(
                "INSERT INTO worker_leases(task_id,worker_id,lease_token,acquired_at,heartbeat_at,expires_at) VALUES(?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET worker_id=excluded.worker_id, lease_token=excluded.lease_token, acquired_at=excluded.acquired_at, heartbeat_at=excluded.heartbeat_at, expires_at=excluded.expires_at",
                (task_id, worker_id, token, self._iso(), self._iso(), now + ttl_seconds),
            )
            self._conn.commit()
        return token

    def heartbeat(self, task_id: str, worker_id: str, lease_token: str, ttl_seconds: float = 30.0) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be > 0")
        with self._lock:
            row = self._conn.execute("SELECT worker_id, lease_token, expires_at FROM worker_leases WHERE task_id=?", (task_id,)).fetchone()
            if not row or row[0] != worker_id or row[1] != lease_token or row[2] <= self._now():
                return False
            self._conn.execute("UPDATE worker_leases SET heartbeat_at=?, expires_at=? WHERE task_id=? AND worker_id=? AND lease_token=?", (self._iso(), self._now() + ttl_seconds, task_id, worker_id, lease_token))
            self._conn.commit()
            return True

    def release(self, task_id: str, worker_id: str, lease_token: str) -> bool:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM worker_leases WHERE task_id=? AND worker_id=? AND lease_token=?", (task_id, worker_id, lease_token))
            self._conn.commit()
            return cursor.rowcount == 1

    def recover_expired(self) -> int:
        with self._lock:
            cursor = self._conn.execute("DELETE FROM worker_leases WHERE expires_at <= ?", (self._now(),))
            self._conn.commit()
            return cursor.rowcount

    def get(self, task_id: str) -> dict[str, object] | None:
        row = self._conn.execute("SELECT task_id,worker_id,lease_token,acquired_at,heartbeat_at,expires_at FROM worker_leases WHERE task_id=?", (task_id,)).fetchone()
        if not row:
            return None
        return {"task_id": row[0], "worker_id": row[1], "lease_token": row[2], "acquired_at": row[3], "heartbeat_at": row[4], "expires_at": row[5], "expired": row[5] <= self._now()}

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg


class AssistantRepository:
    """Conversation repository with PostgreSQL when configured and a bounded in-memory fallback."""

    _memory_sessions: dict[str, dict] = {}
    _memory_messages: dict[str, list[dict]] = {}
    _memory_limit = 100

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("AETHON_DATABASE_URL", "")

    @property
    def enabled(self) -> bool:
        return self.database_url.startswith(("postgres://", "postgresql://"))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def ensure_session(self, session_id: str, owner_id: str, language: str, project_id: str | None = None) -> str:
        if not self.enabled:
            now = self._now()
            session = self._memory_sessions.get(session_id)
            if session is None:
                self._memory_sessions[session_id] = {
                    "session_id": session_id, "owner_id": owner_id, "project_id": project_id,
                    "title": None, "language": language, "created_at": now, "updated_at": now,
                }
            elif session["owner_id"] == owner_id:
                session["language"] = language
                session["updated_at"] = now
            return session_id
        with psycopg.connect(self.database_url) as conn:
            conn.execute(
                """INSERT INTO assistant_sessions(session_id, owner_id, project_id, language)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET language=EXCLUDED.language, updated_at=NOW()""",
                (UUID(session_id), owner_id, project_id, language),
            )
            conn.commit()
        return session_id

    def add_message(self, session_id: str, owner_id: str, role: str, content: str, language: str,
                    intent: str | None = None, action: str | None = None,
                    status: str | None = None, metadata: dict | None = None) -> str:
        message_id = str(uuid4())
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            if session is None or session.get("owner_id") != owner_id:
                return message_id
            self._memory_messages.setdefault(session_id, []).append({
                "message_id": message_id, "role": role, "content": content, "language": language,
                "intent": intent, "action": action, "status": status, "metadata": metadata or {},
                "created_at": self._now(),
            })
            self._memory_messages[session_id] = self._memory_messages[session_id][-self._memory_limit:]
            session["updated_at"] = self._now()
            return message_id
        with psycopg.connect(self.database_url) as conn:
            conn.execute(
                """INSERT INTO assistant_messages
                (message_id, session_id, owner_id, role, content, language, intent, action, status, metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (UUID(message_id), UUID(session_id), owner_id, role, content, language,
                 intent, action, status, json.dumps(metadata or {})),
            )
            conn.commit()
        return message_id

    def history(self, session_id: str, owner_id: str, limit: int = 50) -> list[dict]:
        if not self.enabled:
            rows = self._memory_messages.get(session_id, [])
            if session_id not in self._memory_sessions or self._memory_sessions[session_id].get("owner_id") != owner_id:
                return []
            return rows[-max(1, min(limit, 100)):]
        limit = max(1, min(limit, 100))
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(
                """SELECT message_id, role, content, language, intent, action, status, metadata, created_at
                FROM assistant_messages WHERE session_id=%s AND owner_id=%s
                ORDER BY created_at DESC LIMIT %s""",
                (UUID(session_id), owner_id, limit),
            ).fetchall()
        return [
            {"message_id": str(r[0]), "role": r[1], "content": r[2], "language": r[3],
             "intent": r[4], "action": r[5], "status": r[6], "metadata": r[7],
             "created_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8])}
            for r in reversed(rows)
        ]

    def sessions(self, owner_id: str, limit: int = 50) -> list[dict]:
        if not self.enabled:
            rows = [s for s in self._memory_sessions.values() if s.get("owner_id") == owner_id]
            rows.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return rows[:max(1, min(limit, 100))]
        limit = max(1, min(limit, 100))
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(
                """SELECT session_id, project_id, title, language, created_at, updated_at
                FROM assistant_sessions WHERE owner_id=%s
                ORDER BY updated_at DESC LIMIT %s""",
                (owner_id, limit),
            ).fetchall()
        return [
            {"session_id": str(r[0]), "project_id": r[1], "title": r[2], "language": r[3],
             "created_at": r[4].isoformat() if hasattr(r[4], "isoformat") else str(r[4]),
             "updated_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5])}
            for r in rows
        ]

    def session(self, session_id: str, owner_id: str) -> dict | None:
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            return dict(session) if session and session.get("owner_id") == owner_id else None
        with psycopg.connect(self.database_url) as conn:
            row = conn.execute(
                """SELECT session_id, project_id, title, language, created_at, updated_at
                FROM assistant_sessions WHERE session_id=%s AND owner_id=%s""",
                (UUID(session_id), owner_id),
            ).fetchone()
        if not row:
            return None
        return {
            "session_id": str(row[0]), "project_id": row[1], "title": row[2], "language": row[3],
            "created_at": row[4].isoformat() if hasattr(row[4], "isoformat") else str(row[4]),
            "updated_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]),
        }

    def archive_session(self, session_id: str, owner_id: str) -> bool:
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            if not session or session.get("owner_id") != owner_id:
                return False
            session["title"] = session.get("title") or "Archived"
            session["updated_at"] = self._now()
            return True
        with psycopg.connect(self.database_url) as conn:
            result = conn.execute(
                """UPDATE assistant_sessions SET title=COALESCE(title, 'Archived'), updated_at=NOW()
                WHERE session_id=%s AND owner_id=%s""",
                (UUID(session_id), owner_id),
            )
            conn.commit()
        return result.rowcount == 1

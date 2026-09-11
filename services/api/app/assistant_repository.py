from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg


class AssistantRepository:
    """Owner-scoped conversation persistence with PostgreSQL or bounded development memory."""

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

    @staticmethod
    def _limit(value: int, maximum: int = 100) -> int:
        return max(1, min(value, maximum))

    @staticmethod
    def _search_pattern(query: str) -> str:
        # Escape LIKE metacharacters so user search text is treated literally.
        return "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"

    def ensure_session(self, session_id: str, owner_id: str, language: str, project_id: str | None = None) -> str:
        if not self.enabled:
            now = self._now()
            session = self._memory_sessions.get(session_id)
            if session is None:
                self._memory_sessions[session_id] = {"session_id": session_id, "owner_id": owner_id, "project_id": project_id, "title": None, "language": language, "archived_at": None, "created_at": now, "updated_at": now}
            elif session["owner_id"] == owner_id:
                session["language"] = language
                if project_id is not None:
                    session["project_id"] = project_id
                session["updated_at"] = now
            else:
                raise PermissionError("session belongs to another owner")
            return session_id
        with psycopg.connect(self.database_url) as conn:
            result = conn.execute("""INSERT INTO assistant_sessions(session_id, owner_id, project_id, language)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET language=EXCLUDED.language, updated_at=NOW()
                WHERE assistant_sessions.owner_id = EXCLUDED.owner_id""",
                (UUID(session_id), owner_id, project_id, language))
            conn.commit()
            if result.rowcount != 1:
                raise PermissionError("session belongs to another owner")
        return session_id

    def add_message(self, session_id: str, owner_id: str, role: str, content: str, language: str,
                    intent: str | None = None, action: str | None = None,
                    status: str | None = None, metadata: dict | None = None) -> str:
        message_id = str(uuid4())
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            if session is None or session.get("owner_id") != owner_id:
                raise PermissionError("session not found for owner")
            self._memory_messages.setdefault(session_id, []).append({"message_id": message_id, "role": role, "content": content, "language": language, "intent": intent, "action": action, "status": status, "metadata": metadata or {}, "created_at": self._now()})
            self._memory_messages[session_id] = self._memory_messages[session_id][-self._memory_limit:]
            session["updated_at"] = self._now()
            return message_id
        with psycopg.connect(self.database_url) as conn:
            exists = conn.execute("SELECT 1 FROM assistant_sessions WHERE session_id=%s AND owner_id=%s", (UUID(session_id), owner_id)).fetchone()
            if not exists:
                raise PermissionError("session not found for owner")
            conn.execute("""INSERT INTO assistant_messages
                (message_id, session_id, owner_id, role, content, language, intent, action, status, metadata)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)""",
                (UUID(message_id), UUID(session_id), owner_id, role, content, language, intent, action, status, json.dumps(metadata or {})))
            conn.commit()
        return message_id

    def history(self, session_id: str, owner_id: str, limit: int = 50) -> list[dict]:
        limit = self._limit(limit)
        if not self.enabled:
            rows = self._memory_messages.get(session_id, [])
            if session_id not in self._memory_sessions or self._memory_sessions[session_id].get("owner_id") != owner_id:
                return []
            return rows[-limit:]
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute("""SELECT message_id, role, content, language, intent, action, status, metadata, created_at
                FROM assistant_messages WHERE session_id=%s AND owner_id=%s ORDER BY created_at DESC LIMIT %s""", (UUID(session_id), owner_id, limit)).fetchall()
        return [{"message_id": str(r[0]), "role": r[1], "content": r[2], "language": r[3], "intent": r[4], "action": r[5], "status": r[6], "metadata": r[7], "created_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8])} for r in reversed(rows)]

    def sessions(self, owner_id: str, limit: int = 50, include_archived: bool = False, query: str | None = None) -> list[dict]:
        limit = self._limit(limit)
        q = (query or "").strip().casefold()
        if not self.enabled:
            rows = [s for s in self._memory_sessions.values() if s.get("owner_id") == owner_id and (include_archived or not s.get("archived_at"))]
            if q:
                rows = [s for s in rows if q in str(s.get("title") or "").casefold() or q in str(s.get("session_id") or "").casefold()]
            rows.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return rows[:limit]
        where = "owner_id=%s"
        params: list[object] = [owner_id]
        if not include_archived:
            where += " AND archived_at IS NULL"
        if q:
            where += " AND (COALESCE(title,'') ILIKE %s ESCAPE '\\\\' OR session_id::text ILIKE %s ESCAPE '\\\\')"
            pattern = self._search_pattern(q)
            params.extend([pattern, pattern])
        params.append(limit)
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(f"""SELECT session_id, project_id, title, language, archived_at, created_at, updated_at
                FROM assistant_sessions WHERE {where} ORDER BY updated_at DESC LIMIT %s""", params).fetchall()
        return [{"session_id": str(r[0]), "project_id": r[1], "title": r[2], "language": r[3], "archived_at": r[4].isoformat() if r[4] else None, "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]), "updated_at": r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6])} for r in rows]

    def search_sessions(self, owner_id: str, query: str, limit: int = 50) -> list[dict]:
        return self.sessions(owner_id, limit=limit, include_archived=True, query=query)

    def session(self, session_id: str, owner_id: str) -> dict | None:
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            return dict(session) if session and session.get("owner_id") == owner_id else None
        with psycopg.connect(self.database_url) as conn:
            row = conn.execute("""SELECT session_id, project_id, title, language, archived_at, created_at, updated_at
                FROM assistant_sessions WHERE session_id=%s AND owner_id=%s""", (UUID(session_id), owner_id)).fetchone()
        if not row:
            return None
        return {"session_id": str(row[0]), "project_id": row[1], "title": row[2], "language": row[3], "archived_at": row[4].isoformat() if row[4] else None, "created_at": row[5].isoformat() if hasattr(row[5], "isoformat") else str(row[5]), "updated_at": row[6].isoformat() if hasattr(row[6], "isoformat") else str(row[6])}

    def rename_session(self, session_id: str, owner_id: str, title: str) -> bool:
        title = title.strip()
        if not title or len(title) > 200:
            raise ValueError("title must contain 1-200 characters")
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            if not session or session.get("owner_id") != owner_id:
                return False
            session["title"] = title
            session["updated_at"] = self._now()
            return True
        with psycopg.connect(self.database_url) as conn:
            result = conn.execute("UPDATE assistant_sessions SET title=%s, updated_at=NOW() WHERE session_id=%s AND owner_id=%s", (title, UUID(session_id), owner_id))
            conn.commit()
        return result.rowcount == 1

    def archive_session(self, session_id: str, owner_id: str) -> bool:
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            if not session or session.get("owner_id") != owner_id:
                return False
            session["archived_at"] = session.get("archived_at") or self._now()
            session["updated_at"] = self._now()
            return True
        with psycopg.connect(self.database_url) as conn:
            result = conn.execute("UPDATE assistant_sessions SET archived_at=COALESCE(archived_at,NOW()), updated_at=NOW() WHERE session_id=%s AND owner_id=%s", (UUID(session_id), owner_id))
            conn.commit()
        return result.rowcount == 1

    def delete_session(self, session_id: str, owner_id: str) -> bool:
        if not self.enabled:
            session = self._memory_sessions.get(session_id)
            if not session or session.get("owner_id") != owner_id:
                return False
            self._memory_sessions.pop(session_id, None)
            self._memory_messages.pop(session_id, None)
            return True
        with psycopg.connect(self.database_url) as conn:
            result = conn.execute("DELETE FROM assistant_sessions WHERE session_id=%s AND owner_id=%s", (UUID(session_id), owner_id))
            conn.commit()
        return result.rowcount == 1

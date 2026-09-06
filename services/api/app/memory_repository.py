from __future__ import annotations

import json
import os
from typing import Any

from aethon.memory_engine import MemoryRecord, PersistentMemoryEngine, validate_namespace, redact_secrets, MemorySecurityError, MemoryMatch, _terms, _recency_score


class MemoryRepository:
    """Memory persistence boundary with PostgreSQL durability and local fallback."""

    def __init__(self, database_url: str | None = None, fallback: PersistentMemoryEngine | None = None):
        self.database_url = database_url or os.getenv("AETHON_DATABASE_URL")
        self.fallback = fallback or PersistentMemoryEngine()
        self.use_postgres = bool(self.database_url)
        if self.use_postgres and not self.database_url.startswith(("postgres://", "postgresql://")):
            raise MemorySecurityError("AETHON_DATABASE_URL must be a PostgreSQL URL")

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise MemorySecurityError("psycopg is not installed") from exc
        return psycopg.connect(self.database_url, connect_timeout=5)

    @staticmethod
    def _row_to_record(row: tuple[Any, ...]) -> MemoryRecord:
        return MemoryRecord(memory_id=str(row[0]), content=row[1], namespace=row[2], project_id=row[3],
            memory_type=row[4], source=row[5], confidence=float(row[6]),
            created_at=row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
            updated_at=row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8]),
            expires_at=row[9].isoformat() if row[9] is not None and hasattr(row[9], "isoformat") else row[9],
            owner_id=str(row[10]) if len(row) > 10 else "local-dev")

    def put(self, memory_id: str, content: str, *, owner_id: str = "local-dev", project_id: str | None = None,
            namespace: str = "default", memory_type: str = "semantic", source: str = "agent",
            confidence: float = 1.0, expires_at: str | None = None) -> MemoryRecord:
        if not owner_id.strip():
            raise MemorySecurityError("owner_id is required")
        namespace = validate_namespace(namespace)
        if not memory_id.strip() or not content.strip():
            raise MemorySecurityError("memory id and content are required")
        if not 0.0 <= confidence <= 1.0:
            raise MemorySecurityError("confidence must be between 0 and 1")
        safe_content = redact_secrets(content.strip())
        if not self.use_postgres:
            return self.fallback.put(memory_id, safe_content, owner_id=owner_id, project_id=project_id,
                namespace=namespace, memory_type=memory_type, source=source, confidence=confidence,
                expires_at=expires_at)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """INSERT INTO memories(memory_id, owner_id, project_id, namespace, content, metadata,
                   confidence, source, memory_type, expires_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                   ON CONFLICT (memory_id) DO UPDATE SET owner_id=EXCLUDED.owner_id,
                   project_id=EXCLUDED.project_id, namespace=EXCLUDED.namespace, content=EXCLUDED.content,
                   metadata=EXCLUDED.metadata, confidence=EXCLUDED.confidence, source=EXCLUDED.source,
                   memory_type=EXCLUDED.memory_type, expires_at=EXCLUDED.expires_at, updated_at=NOW()
                   RETURNING memory_id, content, namespace, project_id, memory_type, source,
                   confidence, created_at, updated_at, expires_at, owner_id""",
                (memory_id, owner_id, project_id, namespace, safe_content, json.dumps({"owner_id": owner_id}),
                 confidence, source, memory_type, expires_at),
            )
            return self._row_to_record(cur.fetchone())

    def search(self, query: str, *, owner_id: str = "local-dev", project_id: str | None = None,
               namespace: str = "default", limit: int = 10) -> list[MemoryRecord]:
        if not owner_id.strip():
            raise MemorySecurityError("owner_id is required")
        namespace = validate_namespace(namespace)
        limit = max(1, min(limit, 100))
        if not self.use_postgres:
            return self.fallback.search(query, owner_id=owner_id, project_id=project_id, namespace=namespace, limit=limit)
        terms = _terms(query)
        if not terms:
            return []
        clauses = " OR ".join(["content ILIKE %s" for _ in terms])
        values: list[Any] = [owner_id, project_id, namespace, *[f"%{term}%" for term in terms]]
        sql = f"""SELECT memory_id, content, namespace, project_id, memory_type, source,
                  confidence, created_at, updated_at, expires_at, owner_id
                  FROM memories WHERE owner_id=%s AND project_id IS NOT DISTINCT FROM %s
                  AND namespace=%s AND (expires_at IS NULL OR expires_at > NOW())
                  AND ({clauses}) ORDER BY updated_at DESC LIMIT %s"""
        values.append(min(100, max(limit * 5, limit)))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            candidates = [self._row_to_record(row) for row in cur.fetchall()]
        query_terms = set(terms)
        matches: list[MemoryMatch] = []
        for record in candidates:
            record_terms = set(_terms(f"{record.content} {record.memory_type} {record.source}"))
            lexical = len(query_terms & record_terms) / max(1, len(query_terms))
            recency = _recency_score(record.updated_at)
            score = lexical * 0.65 + recency * 0.15 + record.confidence * 0.20
            matches.append(MemoryMatch(record, score, lexical, recency, record.confidence))
        matches.sort(key=lambda item: (-item.score, -item.record.confidence, item.record.memory_id))
        return [item.record for item in matches[:limit]]

    def delete(self, memory_id: str, *, owner_id: str = "local-dev", project_id: str | None = None,
               namespace: str = "default") -> bool:
        if not owner_id.strip():
            raise MemorySecurityError("owner_id is required")
        namespace = validate_namespace(namespace)
        if not self.use_postgres:
            return self.fallback.delete(memory_id, owner_id=owner_id, project_id=project_id, namespace=namespace)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM memories WHERE memory_id=%s AND owner_id=%s AND project_id IS NOT DISTINCT FROM %s AND namespace=%s",
                (memory_id, owner_id, project_id, namespace))
            return cur.rowcount == 1

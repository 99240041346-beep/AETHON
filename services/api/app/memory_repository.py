from __future__ import annotations

import json
import os
from typing import Any

from aethon.embeddings import EmbeddingError, EmbeddingProvider, build_embedding_provider
from aethon.memory_engine import MemoryMatch, MemoryRecord, MemorySecurityError, PersistentMemoryEngine, _recency_score, _terms, redact_secrets, validate_namespace


class MemoryRepository:
    """Durable memory boundary with scoped PostgreSQL + optional pgvector retrieval."""

    def __init__(self, database_url: str | None = None, fallback: PersistentMemoryEngine | None = None,
                 embedding_provider: EmbeddingProvider | None = None):
        self.database_url = database_url or os.getenv("AETHON_DATABASE_URL")
        self.fallback = fallback or PersistentMemoryEngine()
        self.use_postgres = bool(self.database_url)
        if self.use_postgres and not self.database_url.startswith(("postgres://", "postgresql://")):
            raise MemorySecurityError("AETHON_DATABASE_URL must be a PostgreSQL URL")
        try:
            self.embeddings = embedding_provider or build_embedding_provider()
        except EmbeddingError as exc:
            raise MemorySecurityError(str(exc)) from exc
        self.semantic_enabled = self.use_postgres and not self.embeddings.__class__.__name__.startswith("Disabled")

    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise MemorySecurityError("psycopg is not installed") from exc
        return psycopg.connect(self.database_url, connect_timeout=5)

    @staticmethod
    def _row_to_record(row: tuple[Any, ...]) -> MemoryRecord:
        return MemoryRecord(
            memory_id=str(row[0]), content=row[1], namespace=row[2], project_id=row[3],
            memory_type=row[4], source=row[5], confidence=float(row[6]),
            created_at=row[7].isoformat() if hasattr(row[7], "isoformat") else str(row[7]),
            updated_at=row[8].isoformat() if hasattr(row[8], "isoformat") else str(row[8]),
            expires_at=row[9].isoformat() if row[9] is not None and hasattr(row[9], "isoformat") else row[9],
            owner_id=str(row[10]) if len(row) > 10 else "local-dev",
        )

    def _embed(self, text: str) -> list[float] | None:
        if not self.semantic_enabled:
            return None
        try:
            return self.embeddings.embed(text)
        except EmbeddingError as exc:
            raise MemorySecurityError(str(exc)) from exc

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
                                     namespace=namespace, memory_type=memory_type, source=source,
                                     confidence=confidence, expires_at=expires_at)
        embedding = self._embed(safe_content)
        with self._connect() as conn, conn.cursor() as cur:
            if embedding is None:
                cur.execute(
                    """INSERT INTO memories(memory_id, owner_id, project_id, namespace, content, metadata,
                       confidence, source, memory_type, expires_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                       ON CONFLICT (memory_id) DO UPDATE SET content=EXCLUDED.content,
                       metadata=EXCLUDED.metadata, confidence=EXCLUDED.confidence, source=EXCLUDED.source,
                       memory_type=EXCLUDED.memory_type, expires_at=EXCLUDED.expires_at, updated_at=NOW()
                       WHERE memories.owner_id=EXCLUDED.owner_id
                         AND memories.project_id IS NOT DISTINCT FROM EXCLUDED.project_id
                         AND memories.namespace=EXCLUDED.namespace
                       RETURNING memory_id, content, namespace, project_id, memory_type, source,
                       confidence, created_at, updated_at, expires_at, owner_id""",
                    (memory_id, owner_id, project_id, namespace, safe_content, json.dumps({"owner_id": owner_id}),
                     confidence, source, memory_type, expires_at),
                )
            else:
                vector_literal = "[" + ",".join(str(float(v)) for v in embedding) + "]"
                cur.execute(
                    """INSERT INTO memories(memory_id, owner_id, project_id, namespace, content, metadata,
                       confidence, source, memory_type, expires_at, embedding, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,NOW())
                       ON CONFLICT (memory_id) DO UPDATE SET content=EXCLUDED.content,
                       metadata=EXCLUDED.metadata, confidence=EXCLUDED.confidence, source=EXCLUDED.source,
                       memory_type=EXCLUDED.memory_type, expires_at=EXCLUDED.expires_at,
                       embedding=EXCLUDED.embedding, updated_at=NOW()
                       WHERE memories.owner_id=EXCLUDED.owner_id
                         AND memories.project_id IS NOT DISTINCT FROM EXCLUDED.project_id
                         AND memories.namespace=EXCLUDED.namespace
                       RETURNING memory_id, content, namespace, project_id, memory_type, source,
                       confidence, created_at, updated_at, expires_at, owner_id""",
                    (memory_id, owner_id, project_id, namespace, safe_content, json.dumps({"owner_id": owner_id}),
                     confidence, source, memory_type, expires_at, vector_literal),
                )
            row = cur.fetchone()
            if row is None:
                raise MemorySecurityError("memory id belongs to another authorized scope")
            return self._row_to_record(row)

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
        embedding = self._embed(query)
        candidate_limit = min(100, max(limit * 5, limit))
        clauses = " OR ".join(["content ILIKE %s" for _ in terms])
        lexical_values: list[Any] = [owner_id, project_id, namespace, *[f"%{term}%" for term in terms]]
        if embedding is not None:
            vector_literal = "[" + ",".join(str(float(v)) for v in embedding) + "]"
            sql = f"""WITH scoped AS (
                SELECT memory_id, content, namespace, project_id, memory_type, source, confidence,
                       created_at, updated_at, expires_at, owner_id,
                       (1 - (embedding <=> %s::vector)) AS semantic_score,
                       CASE WHEN ({clauses}) THEN 1.0 ELSE 0.0 END AS lexical_score
                FROM memories
                WHERE owner_id=%s AND project_id IS NOT DISTINCT FROM %s AND namespace=%s
                  AND (expires_at IS NULL OR expires_at > NOW()) AND embedding IS NOT NULL
            )
            SELECT * FROM scoped ORDER BY (semantic_score * 0.55 + lexical_score * 0.25 + confidence * 0.10 +
                GREATEST(0.0, EXP(-EXTRACT(EPOCH FROM (NOW()-updated_at))/86400.0/30.0)) * 0.10) DESC
            LIMIT %s"""
            values = [vector_literal, owner_id, project_id, namespace, *[f"%{term}%" for term in terms], candidate_limit]
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(sql, tuple(values))
                return [self._row_to_record(row) for row in cur.fetchall()]
        sql = f"""SELECT memory_id, content, namespace, project_id, memory_type, source,
                  confidence, created_at, updated_at, expires_at, owner_id
                  FROM memories WHERE owner_id=%s AND project_id IS NOT DISTINCT FROM %s
                  AND namespace=%s AND (expires_at IS NULL OR expires_at > NOW())
                  AND ({clauses}) ORDER BY updated_at DESC LIMIT %s"""
        values = lexical_values + [candidate_limit]
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

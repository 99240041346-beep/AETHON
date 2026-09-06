from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock

_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_ -]?key|secret|password|token|private[_ -]?key)\b\s*[:=]\s*\S+"),
    re.compile(r"\b(?:sk|pk)_[A-Za-z0-9_-]{16,}\b"),
)


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    content: str
    namespace: str
    project_id: str | None
    memory_type: str
    source: str
    confidence: float
    created_at: str
    updated_at: str
    expires_at: str | None = None


class MemorySecurityError(ValueError):
    pass


def redact_secrets(text: str) -> str:
    result = text
    for pattern in _SECRET_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def validate_namespace(namespace: str) -> str:
    namespace = namespace.strip()
    if not namespace or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", namespace):
        raise MemorySecurityError("invalid memory namespace")
    return namespace


class PersistentMemoryEngine:
    """Thread-safe memory runtime with project/namespace isolation."""

    def __init__(self):
        self._records: dict[str, MemoryRecord] = {}
        self._lock = RLock()

    def put(
        self,
        memory_id: str,
        content: str,
        *,
        project_id: str | None = None,
        namespace: str = "default",
        memory_type: str = "semantic",
        source: str = "agent",
        confidence: float = 1.0,
        expires_at: str | None = None,
    ) -> MemoryRecord:
        namespace = validate_namespace(namespace)
        if not memory_id.strip() or not content.strip():
            raise MemorySecurityError("memory id and content are required")
        if not 0.0 <= confidence <= 1.0:
            raise MemorySecurityError("confidence must be between 0 and 1")
        safe_content = redact_secrets(content.strip())
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            old = self._records.get(memory_id)
            record = MemoryRecord(
                memory_id=memory_id,
                content=safe_content,
                namespace=namespace,
                project_id=project_id,
                memory_type=memory_type,
                source=source,
                confidence=confidence,
                created_at=old.created_at if old else now,
                updated_at=now,
                expires_at=expires_at,
            )
            self._records[memory_id] = record
            return record

    def search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        namespace: str = "default",
        limit: int = 10,
    ) -> list[MemoryRecord]:
        namespace = validate_namespace(namespace)
        limit = max(1, min(limit, 100))
        terms = [t for t in re.findall(r"[\w-]+", query.lower()) if t]
        now = datetime.now(timezone.utc)
        scored: list[tuple[float, MemoryRecord]] = []
        with self._lock:
            records = list(self._records.values())
        for record in records:
            if record.namespace != namespace or record.project_id != project_id:
                continue
            if record.expires_at:
                try:
                    if datetime.fromisoformat(record.expires_at) <= now:
                        continue
                except ValueError:
                    continue
            haystack = f"{record.content} {record.memory_type} {record.source}".lower()
            hits = sum(1 for term in terms if term in haystack)
            if terms and hits == 0:
                continue
            score = (hits / max(1, len(terms))) * 0.8 + record.confidence * 0.2
            scored.append((score, record))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def delete(self, memory_id: str, *, project_id: str | None = None, namespace: str = "default") -> bool:
        namespace = validate_namespace(namespace)
        with self._lock:
            record = self._records.get(memory_id)
            if not record or record.project_id != project_id or record.namespace != namespace:
                return False
            del self._records[memory_id]
            return True

    def count(self, *, project_id: str | None = None, namespace: str = "default") -> int:
        namespace = validate_namespace(namespace)
        with self._lock:
            return sum(1 for r in self._records.values() if r.project_id == project_id and r.namespace == namespace)


# API and task execution share this runtime boundary. Callers/tests can still
# inject an isolated PersistentMemoryEngine into AgentRuntime when needed.
default_memory_engine = PersistentMemoryEngine()

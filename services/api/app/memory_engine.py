from __future__ import annotations

import math
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
    owner_id: str = "local-dev"


@dataclass(frozen=True)
class MemoryMatch:
    record: MemoryRecord
    score: float
    lexical_score: float
    recency_score: float
    confidence_score: float


@dataclass(frozen=True)
class MemoryConflict:
    key: str
    memory_ids: list[str]
    values: list[str]


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


def _terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[\w-]+", text.lower()) if len(term) > 1]


def _recency_score(updated_at: str) -> float:
    try:
        stamp = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age_days = max(0.0, (datetime.now(timezone.utc) - stamp).total_seconds() / 86400.0)
        return math.exp(-age_days / 30.0)
    except (ValueError, TypeError):
        return 0.0


def _memory_key(content: str) -> str | None:
    match = re.match(r"\s*([A-Za-z][A-Za-z0-9_. -]{1,80})\s*[:=]\s*(.+)", content)
    return match.group(1).strip().lower() if match else None


def detect_memory_conflicts(records: list[MemoryRecord]) -> list[MemoryConflict]:
    """Detect conservative conflicts only when records explicitly share a key.

    A conflict is a review signal, never an automatic instruction to delete or
    overwrite memory. Records remain intact until a higher-level policy decides.
    """
    groups: dict[str, list[MemoryRecord]] = {}
    for record in records:
        key = _memory_key(record.content)
        if key:
            groups.setdefault(key, []).append(record)
    conflicts: list[MemoryConflict] = []
    for key, items in groups.items():
        values = {re.sub(r"\s+", " ", item.content.split(":", 1)[-1].split("=", 1)[-1]).strip().lower() for item in items}
        if len(values) > 1:
            conflicts.append(MemoryConflict(key, [item.memory_id for item in items], sorted(values)))
    return conflicts


class PersistentMemoryEngine:
    """Thread-safe development memory with owner/project/namespace isolation."""

    def __init__(self):
        self._records: dict[str, MemoryRecord] = {}
        self._lock = RLock()

    def put(self, memory_id: str, content: str, *, owner_id: str = "local-dev", project_id: str | None = None,
            namespace: str = "default", memory_type: str = "semantic", source: str = "agent",
            confidence: float = 1.0, expires_at: str | None = None) -> MemoryRecord:
        namespace = validate_namespace(namespace)
        if not owner_id.strip() or not memory_id.strip() or not content.strip():
            raise MemorySecurityError("owner_id, memory id and content are required")
        if not 0.0 <= confidence <= 1.0:
            raise MemorySecurityError("confidence must be between 0 and 1")
        safe_content = redact_secrets(content.strip())
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            old = self._records.get(memory_id)
            if old and (old.owner_id != owner_id or old.project_id != project_id or old.namespace != namespace):
                raise MemorySecurityError("memory id belongs to another authorized scope")
            record = MemoryRecord(memory_id=memory_id, content=safe_content, namespace=namespace,
                project_id=project_id, memory_type=memory_type, source=source, confidence=confidence,
                created_at=old.created_at if old else now, updated_at=now, expires_at=expires_at, owner_id=owner_id)
            self._records[memory_id] = record
            return record

    def search_matches(self, query: str, *, owner_id: str = "local-dev", project_id: str | None = None,
                       namespace: str = "default", limit: int = 10) -> list[MemoryMatch]:
        namespace = validate_namespace(namespace)
        if not owner_id.strip():
            raise MemorySecurityError("owner_id is required")
        limit = max(1, min(limit, 100))
        query_terms = set(_terms(query))
        now = datetime.now(timezone.utc)
        matches: list[MemoryMatch] = []
        with self._lock:
            records = list(self._records.values())
        for record in records:
            if record.owner_id != owner_id or record.namespace != namespace or record.project_id != project_id:
                continue
            if record.expires_at:
                try:
                    if datetime.fromisoformat(record.expires_at.replace("Z", "+00:00")) <= now:
                        continue
                except ValueError:
                    continue
            record_terms = set(_terms(f"{record.content} {record.memory_type} {record.source}"))
            lexical = len(query_terms & record_terms) / max(1, len(query_terms)) if query_terms else 0.0
            if query_terms and lexical == 0:
                continue
            recency = _recency_score(record.updated_at)
            confidence = record.confidence
            score = lexical * 0.65 + recency * 0.15 + confidence * 0.20
            matches.append(MemoryMatch(record, score, lexical, recency, confidence))
        matches.sort(key=lambda item: (-item.score, -item.record.confidence, item.record.memory_id))
        return matches[:limit]

    def search(self, query: str, *, owner_id: str = "local-dev", project_id: str | None = None,
               namespace: str = "default", limit: int = 10) -> list[MemoryRecord]:
        return [match.record for match in self.search_matches(query, owner_id=owner_id,
            project_id=project_id, namespace=namespace, limit=limit)]

    def consolidate_candidates(self, *, owner_id: str = "local-dev", project_id: str | None = None,
                               namespace: str = "default", limit: int = 100) -> dict[str, object]:
        namespace = validate_namespace(namespace)
        with self._lock:
            records = [r for r in self._records.values()
                       if r.owner_id == owner_id and r.project_id == project_id and r.namespace == namespace]
        records = records[:max(1, min(limit, 1000))]
        conflicts = detect_memory_conflicts(records)
        by_content: dict[str, list[MemoryRecord]] = {}
        for record in records:
            by_content.setdefault(re.sub(r"\s+", " ", record.content.strip()).lower(), []).append(record)
        duplicates = [[item.memory_id for item in group] for group in by_content.values() if len(group) > 1]
        return {"records_considered": len(records), "duplicate_groups": duplicates, "conflicts": [conflict.__dict__ for conflict in conflicts]}

    def delete(self, memory_id: str, *, owner_id: str = "local-dev", project_id: str | None = None,
               namespace: str = "default") -> bool:
        namespace = validate_namespace(namespace)
        with self._lock:
            record = self._records.get(memory_id)
            if not record or record.owner_id != owner_id or record.project_id != project_id or record.namespace != namespace:
                return False
            del self._records[memory_id]
            return True

    def count(self, *, owner_id: str = "local-dev", project_id: str | None = None, namespace: str = "default") -> int:
        namespace = validate_namespace(namespace)
        with self._lock:
            return sum(1 for r in self._records.values()
                       if r.owner_id == owner_id and r.project_id == project_id and r.namespace == namespace)


default_memory_engine = PersistentMemoryEngine()

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from aethon.memory_engine import MemoryRecord, _recency_score, detect_memory_conflicts


@dataclass(frozen=True)
class MemoryImportance:
    memory_id: str
    score: float
    confidence: float
    recency: float
    source_value: float
    type_value: float
    content_value: float


@dataclass(frozen=True)
class MemoryPromotion:
    memory_id: str
    from_type: str
    to_type: str
    score: float
    reason: str


@dataclass(frozen=True)
class MemoryForgetCandidate:
    memory_id: str
    score: float
    reason: str


_SOURCE_VALUE = {"user": 1.0, "verified_task_result": 0.95, "system": 0.9, "agent": 0.7, "import": 0.5}
_TYPE_VALUE = {"preference": 1.0, "semantic": 0.9, "episodic": 0.85, "project": 0.85, "working": 0.35}


def _content_signal(content: str) -> float:
    text = content.strip()
    if not text:
        return 0.0
    stable = bool(re.search(r"\b(always|never|prefer|preference|important|critical|deadline|architecture|decision)\b", text, re.I))
    structured = bool(re.match(r"\s*[A-Za-z][A-Za-z0-9_. -]{1,80}\s*[:=]", text))
    length_bonus = min(1.0, len(text) / 500.0)
    return min(1.0, 0.45 * stable + 0.25 * structured + 0.30 * length_bonus)


def importance(record: MemoryRecord) -> MemoryImportance:
    recency = _recency_score(record.updated_at)
    source_value = _SOURCE_VALUE.get(record.source.lower(), 0.5)
    type_value = _TYPE_VALUE.get(record.memory_type.lower(), 0.5)
    content_value = _content_signal(record.content)
    score = 0.30 * record.confidence + 0.20 * recency + 0.15 * source_value + 0.15 * type_value + 0.20 * content_value
    return MemoryImportance(record.memory_id, round(score, 6), record.confidence, recency, source_value, type_value, content_value)


def rank_importance(records: list[MemoryRecord]) -> list[MemoryImportance]:
    return sorted((importance(r) for r in records), key=lambda item: (-item.score, item.memory_id))


def deduplicate(records: list[MemoryRecord]) -> dict[str, object]:
    groups: dict[str, list[MemoryRecord]] = {}
    for record in records:
        key = re.sub(r"\s+", " ", record.content.strip()).lower()
        groups.setdefault(key, []).append(record)
    duplicate_groups = []
    canonical: dict[str, str] = {}
    for items in groups.values():
        if len(items) < 2:
            continue
        ranked = sorted(items, key=lambda r: (-importance(r).score, r.memory_id))
        duplicate_groups.append([r.memory_id for r in ranked])
        for duplicate in ranked:
            canonical[duplicate.memory_id] = ranked[0].memory_id
    return {"duplicate_groups": duplicate_groups, "canonical_by_memory_id": canonical}


def resolve_contradictions(records: list[MemoryRecord]) -> dict[str, object]:
    conflicts = detect_memory_conflicts(records)
    by_id = {record.memory_id: record for record in records}
    resolutions = []
    for conflict in conflicts:
        ranked = sorted((by_id[mid] for mid in conflict.memory_ids), key=lambda r: (-importance(r).score, r.memory_id))
        resolutions.append({"key": conflict.key, "winner_memory_id": ranked[0].memory_id,
                            "candidate_memory_ids": conflict.memory_ids,
                            "reason": "highest deterministic importance; review required before destructive change"})
    return {"conflicts": [c.__dict__ for c in conflicts], "resolutions": resolutions}


def compress_context(records: list[MemoryRecord], *, max_chars: int = 6000) -> list[MemoryRecord]:
    max_chars = max(500, min(max_chars, 50000))
    selected: list[MemoryRecord] = []
    used = 0
    for record in sorted(records, key=lambda r: (-importance(r).score, r.memory_id)):
        cost = len(record.content) + 64
        if selected and used + cost > max_chars:
            continue
        selected.append(record)
        used += cost
        if used >= max_chars:
            break
    return selected


def promotion_plan(records: list[MemoryRecord]) -> list[MemoryPromotion]:
    result = []
    for record in records:
        score = importance(record).score
        target = None
        if record.memory_type == "working" and score >= 0.78:
            target = "episodic"
        elif record.memory_type == "episodic" and score >= 0.88:
            target = "semantic"
        elif record.memory_type == "semantic" and record.project_id and score >= 0.90:
            target = "project"
        if target:
            result.append(MemoryPromotion(record.memory_id, record.memory_type, target, score, "importance threshold exceeded"))
    return result


def forgetting_candidates(records: list[MemoryRecord], *, threshold: float = 0.25) -> list[MemoryForgetCandidate]:
    threshold = max(0.0, min(threshold, 1.0))
    now = datetime.now(timezone.utc)
    result = []
    for record in records:
        expired = False
        if record.expires_at:
            try:
                expired = datetime.fromisoformat(record.expires_at.replace("Z", "+00:00")) <= now
            except ValueError:
                expired = True
        score = importance(record).score
        if expired:
            result.append(MemoryForgetCandidate(record.memory_id, score, "expired"))
        elif score < threshold and record.memory_type == "working":
            result.append(MemoryForgetCandidate(record.memory_id, score, "low-importance working memory"))
    return sorted(result, key=lambda item: (item.score, item.memory_id))


def maintenance_plan(records: list[MemoryRecord], *, max_chars: int = 6000, forget_threshold: float = 0.25) -> dict[str, object]:
    return {
        "importance": [item.__dict__ for item in rank_importance(records)],
        "deduplication": deduplicate(records),
        "contradictions": resolve_contradictions(records),
        "promotion": [item.__dict__ for item in promotion_plan(records)],
        "forgetting": [item.__dict__ for item in forgetting_candidates(records, threshold=forget_threshold)],
        "compressed_context_ids": [item.memory_id for item in compress_context(records, max_chars=max_chars)],
    }

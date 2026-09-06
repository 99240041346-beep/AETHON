from datetime import datetime, timedelta, timezone

from aethon.memory_engine import PersistentMemoryEngine
from aethon.memory_intelligence import (
    compress_context,
    deduplicate,
    forgetting_candidates,
    importance,
    promotion_plan,
    resolve_contradictions,
)


def test_importance_prefers_confident_user_preference():
    memory = PersistentMemoryEngine()
    record = memory.put("p", "preferred editor: VS Code", owner_id="a", project_id="x", namespace="project", memory_type="preference", source="user", confidence=1.0)
    assert importance(record).score > 0.7


def test_deduplication_selects_highest_value_canonical():
    memory = PersistentMemoryEngine()
    low = memory.put("a", "preferred framework: FastAPI", confidence=0.4)
    high = memory.put("b", "preferred framework: FastAPI", confidence=1.0, source="user", memory_type="preference")
    report = deduplicate([low, high])
    assert report["canonical_by_memory_id"]["a"] == "b"
    assert report["canonical_by_memory_id"]["b"] == "b"


def test_contradiction_resolution_is_non_destructive():
    memory = PersistentMemoryEngine()
    old = memory.put("a", "database: sqlite", confidence=0.5)
    new = memory.put("b", "database: postgres", confidence=1.0, source="user")
    result = resolve_contradictions([old, new])
    assert result["resolutions"][0]["winner_memory_id"] == "b"
    assert len(result["conflicts"]) == 1


def test_context_compression_respects_budget():
    memory = PersistentMemoryEngine()
    records = [memory.put(str(i), f"important memory {i} " + "x" * 300) for i in range(10)]
    selected = compress_context(records, max_chars=1000)
    assert len(selected) < len(records)
    assert sum(len(r.content) + 64 for r in selected) <= 1000


def test_working_memory_can_be_promoted():
    memory = PersistentMemoryEngine()
    record = memory.put("w", "important architecture decision: use FastAPI", memory_type="working", source="user", confidence=1.0, project_id="p")
    plan = promotion_plan([record])
    assert plan and plan[0].to_type == "episodic"


def test_expired_memory_is_forgetting_candidate():
    memory = PersistentMemoryEngine()
    expired = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    record = memory.put("old", "temporary context", memory_type="working", expires_at=expired)
    candidates = forgetting_candidates([record])
    assert candidates[0].memory_id == "old"
    assert candidates[0].reason == "expired"

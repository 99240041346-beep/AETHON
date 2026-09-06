from aethon.memory_engine import MemorySecurityError, PersistentMemoryEngine, detect_memory_conflicts


def test_memory_is_project_and_namespace_isolated():
    memory = PersistentMemoryEngine()
    memory.put("a", "alpha project architecture", project_id="alpha", namespace="project")
    memory.put("b", "beta project architecture", project_id="beta", namespace="project")
    assert [r.memory_id for r in memory.search("architecture", project_id="alpha", namespace="project")] == ["a"]


def test_memory_ranks_relevant_high_confidence_items():
    memory = PersistentMemoryEngine()
    memory.put("weak", "python project", project_id="p", namespace="project", confidence=0.2)
    memory.put("strong", "python project python", project_id="p", namespace="project", confidence=1.0)
    assert memory.search("python", project_id="p", namespace="project")[0].memory_id == "strong"


def test_memory_redacts_secrets():
    memory = PersistentMemoryEngine()
    record = memory.put("secret", "API_KEY=super-secret-value", project_id="p")
    assert "super-secret-value" not in record.content
    assert "[REDACTED]" in record.content


def test_invalid_namespace_rejected():
    try:
        PersistentMemoryEngine().put("x", "data", namespace="bad namespace")
        assert False
    except MemorySecurityError:
        pass


def test_delete_requires_matching_scope():
    memory = PersistentMemoryEngine()
    memory.put("x", "data", project_id="p", namespace="project")
    assert memory.delete("x", project_id="other", namespace="project") is False
    assert memory.delete("x", project_id="p", namespace="project") is True


def test_memory_owner_isolation():
    memory = PersistentMemoryEngine()
    memory.put("x", "private architecture", owner_id="alice", project_id="p", namespace="project")
    memory.put("y", "private architecture", owner_id="bob", project_id="p", namespace="project")
    assert [r.memory_id for r in memory.search("architecture", owner_id="alice", project_id="p", namespace="project")] == ["x"]


def test_conflict_analysis_requires_explicit_key():
    memory = PersistentMemoryEngine()
    a = memory.put("a", "database: postgres", project_id="p", namespace="project")
    b = memory.put("b", "database: sqlite", project_id="p", namespace="project")
    conflicts = detect_memory_conflicts([a, b])
    assert len(conflicts) == 1
    assert conflicts[0].key == "database"
    assert set(conflicts[0].memory_ids) == {"a", "b"}


def test_consolidation_reports_duplicates_without_deleting():
    memory = PersistentMemoryEngine()
    memory.put("a", "preferred framework: FastAPI", project_id="p", namespace="project")
    memory.put("b", "preferred framework: FastAPI", project_id="p", namespace="project")
    report = memory.consolidate_candidates(owner_id="local-dev", project_id="p", namespace="project")
    assert report["records_considered"] == 2
    assert ["a", "b"] in report["duplicate_groups"]
    assert memory.count(project_id="p", namespace="project") == 2

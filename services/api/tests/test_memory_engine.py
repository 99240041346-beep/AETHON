from aethon.memory_engine import MemorySecurityError, PersistentMemoryEngine


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

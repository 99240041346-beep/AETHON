from app.memory_commands import NaturalMemory
from aethon.memory_repository import MemoryRepository


def test_natural_memory_remember_search_forget():
    memory = NaturalMemory(MemoryRepository())
    remembered = memory.execute(memory.parse("remember preferred editor: VS Code"), owner_id="owner-1")
    assert remembered["action"] == "remembered"

    found = memory.execute(memory.parse("what do you remember about preferred editor"), owner_id="owner-1")
    assert found["memories"]
    assert "VS Code" in found["memories"][0]["content"]

    forgotten = memory.execute(memory.parse("forget preferred editor"), owner_id="owner-1")
    assert forgotten["count"] == 1


def test_natural_memory_is_owner_scoped():
    memory = NaturalMemory(MemoryRepository())
    memory.execute(memory.parse("remember favorite language: Python"), owner_id="owner-1")
    found = memory.execute(memory.parse("recall favorite language"), owner_id="owner-2")
    assert found["memories"] == []


def test_natural_memory_never_stores_secret_material():
    memory = NaturalMemory(MemoryRepository())
    result = memory.execute(memory.parse("remember api_key: sk_test_12345678901234567890"), owner_id="owner-1")
    assert result["memory"]["content"] == "[REDACTED]"

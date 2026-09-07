from types import SimpleNamespace
from uuid import uuid4

from aethon.agent import AgentRuntime
from aethon.schemas import Task


class FakeMemory:
    def __init__(self):
        self.writes = []

    def put(self, memory_id, content, **kwargs):
        self.writes.append((memory_id, content, kwargs))
        return SimpleNamespace(memory_id=memory_id, namespace=kwargs["namespace"])


def test_verified_learning_is_persisted_in_task_scope():
    memory = FakeMemory()
    runtime = AgentRuntime(memory=memory)
    task = Task(task_id=uuid4(), goal="Research AETHON", owner_id="owner-a", project_id="project-a")

    runtime._persist_learning(task, "project", "verified result")

    assert len(memory.writes) == 1
    memory_id, content, kwargs = memory.writes[0]
    assert memory_id.startswith(f"learning:{task.task_id}:")
    assert "Goal: Research AETHON" in content
    assert kwargs["owner_id"] == "owner-a"
    assert kwargs["project_id"] == "project-a"
    assert kwargs["namespace"] == "project"
    assert kwargs["memory_type"] == "semantic"
    assert kwargs["source"] == "agent_learning"
    assert kwargs["confidence"] == 1.0


def test_learning_persistence_does_not_cross_scope():
    memory = FakeMemory()
    runtime = AgentRuntime(memory=memory)
    task = Task(task_id=uuid4(), goal="goal", owner_id="owner-a", project_id="project-a")

    runtime._persist_learning(task, "project", "result")

    assert memory.writes[0][2]["owner_id"] == "owner-a"
    assert memory.writes[0][2]["project_id"] == "project-a"
    assert memory.writes[0][2]["namespace"] == "project"

from __future__ import annotations

from aethon.memory import MemoryItem
from aethon.memory_engine import PersistentMemoryEngine


class AgentMemoryAdapter:
    """Adapter exposing the legacy MemoryStore contract over the secure engine."""

    def __init__(self, engine: PersistentMemoryEngine | None = None):
        self.engine = engine or PersistentMemoryEngine()

    def put(self, key, value, project_id=None):
        return self.engine.put(key, str(value), project_id=project_id, namespace="project" if project_id else "default")

    def search(self, query, project_id=None, limit=10):
        namespace = "project" if project_id else "default"
        records = self.engine.search(query, project_id=project_id, namespace=namespace, limit=limit)
        return [MemoryItem(key=r.memory_id, value=r.content, project_id=r.project_id) for r in records]

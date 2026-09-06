from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from aethon.memory_engine import PersistentMemoryEngine, MemorySecurityError


class MemoryWriteRequest(BaseModel):
    memory_id: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    project_id: str | None = Field(default=None, max_length=200)
    namespace: str = Field(default="default", max_length=128)
    memory_type: str = Field(default="semantic", max_length=64)
    source: str = Field(default="agent", max_length=128)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    expires_at: str | None = None


class MemorySearchRequest(BaseModel):
    query: str = Field(default="", max_length=10000)
    project_id: str | None = Field(default=None, max_length=200)
    namespace: str = Field(default="default", max_length=128)
    limit: int = Field(default=10, ge=1, le=100)


class MemoryDeleteRequest(BaseModel):
    project_id: str | None = None
    namespace: str = "default"


memory_engine = PersistentMemoryEngine()


def write_memory(request: MemoryWriteRequest) -> dict[str, Any]:
    return memory_engine.put(
        request.memory_id, request.content, project_id=request.project_id,
        namespace=request.namespace, memory_type=request.memory_type,
        source=request.source, confidence=request.confidence,
        expires_at=request.expires_at,
    ).__dict__


def search_memory(request: MemorySearchRequest) -> list[dict[str, Any]]:
    return [r.__dict__ for r in memory_engine.search(
        request.query, project_id=request.project_id,
        namespace=request.namespace, limit=request.limit,
    )]


def delete_memory(memory_id: str, request: MemoryDeleteRequest) -> bool:
    return memory_engine.delete(memory_id, project_id=request.project_id, namespace=request.namespace)

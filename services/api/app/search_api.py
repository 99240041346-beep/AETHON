from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from aethon.auth import current_owner, security
from app.assistant_repository import AssistantRepository
from aethon.memory_repository import MemoryRepository


router = APIRouter(prefix="/v1/search", tags=["search"])
sessions = AssistantRepository()
memory = MemoryRepository()


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


@router.get("")
def global_search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=20, ge=1, le=100), owner_id: str = Depends(owner)):
    session_rows = sessions.search_sessions(owner_id, q, limit)
    memory_rows = memory.search(q, owner_id=owner_id, namespace="default", limit=limit)
    project_rows = memory.search(q, owner_id=owner_id, namespace="projects", limit=limit)
    return {
        "ok": True,
        "query": q,
        "results": {
            "conversations": session_rows[:limit],
            "memory": [item.__dict__ for item in memory_rows[:limit]],
            "projects": [item.__dict__ for item in project_rows[:limit]],
        },
    }

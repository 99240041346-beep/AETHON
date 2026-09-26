from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from aethon.memory_repository import MemoryRepository


router = APIRouter(prefix="/v1/projects", tags=["projects"])
memory = MemoryRepository()


class ProjectCreate(BaseModel):
    model_config = {"extra": "forbid"}
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=5000)
    instructions: str = Field(default="", max_length=10000)


class ProjectPatch(BaseModel):
    model_config = {"extra": "forbid"}
    name: str | None = Field(default=None, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    instructions: str | None = Field(default=None, max_length=10000)


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


def _decode(record):
    value = json.loads(record.content)
    value["project_id"] = record.memory_id.removeprefix("project:")
    return value


@router.post("")
def create_project(request: ProjectCreate, owner_id: str = Depends(owner)):
    project_id = str(uuid4())
    value = {
        "name": request.name.strip(),
        "description": request.description.strip(),
        "instructions": request.instructions.strip(),
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    record = memory.put(
        "project:" + project_id, json.dumps(value), owner_id=owner_id,
        namespace="projects", memory_type="project", source="project_api", confidence=1.0,
    )
    return {"ok": True, "project": _decode(record)}


@router.get("")
def list_projects(owner_id: str = Depends(owner)):
    records = memory.list_scope(owner_id=owner_id, namespace="projects", limit=200)
    return {"ok": True, "projects": [_decode(record) for record in records]}


@router.get("/{project_id}")
def get_project(project_id: str, owner_id: str = Depends(owner)):
    records = memory.list_scope(owner_id=owner_id, namespace="projects", limit=200)
    for record in records:
        if record.memory_id == "project:" + project_id:
            return {"ok": True, "project": _decode(record)}
    raise HTTPException(404, "project not found")


@router.patch("/{project_id}")
def patch_project(project_id: str, request: ProjectPatch, owner_id: str = Depends(owner)):
    records = memory.list_scope(owner_id=owner_id, namespace="projects", limit=200)
    current = next((record for record in records if record.memory_id == "project:" + project_id), None)
    if current is None:
        raise HTTPException(404, "project not found")
    value = _decode(current)
    for field in ("name", "description", "instructions"):
        incoming = getattr(request, field)
        if incoming is not None:
            value[field] = incoming.strip()
    record = memory.put(current.memory_id, json.dumps(value), owner_id=owner_id,
                        namespace="projects", memory_type="project", source="project_api", confidence=1.0)
    return {"ok": True, "project": _decode(record)}


@router.delete("/{project_id}")
def delete_project(project_id: str, owner_id: str = Depends(owner)):
    deleted = memory.delete("project:" + project_id, owner_id=owner_id, namespace="projects")
    if not deleted:
        raise HTTPException(404, "project not found")
    return {"ok": True, "project_id": project_id, "deleted": True}

from __future__ import annotations

from threading import RLock
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.agent import AgentRuntime
from aethon.auth import current_owner, security
from aethon.schemas import Task, TaskStatus


router = APIRouter(prefix="/v1/agents", tags=["agents"])
_runtime = AgentRuntime()
_tasks: dict[str, Task] = {}
_lock = RLock()


class AgentRunRequest(BaseModel):
    model_config = {"extra": "forbid"}

    goal: str = Field(min_length=3, max_length=10000)
    project_id: str | None = Field(default=None, max_length=200)
    priority: int = Field(default=5, ge=1, le=10)


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


@router.post("/run")
def run_agent(request: AgentRunRequest, owner_id: str = Depends(owner)) -> dict:
    task = Task(
        task_id=uuid4(),
        goal=request.goal,
        project_id=request.project_id,
        priority=request.priority,
        owner_id=owner_id,
        status=TaskStatus.QUEUED,
    )
    with _lock:
        _tasks[str(task.task_id)] = task
    try:
        result = _runtime.run(task)
    except Exception as exc:
        task.status = TaskStatus.FAILED
        task.error = str(exc)
        result = task
    with _lock:
        _tasks[str(result.task_id)] = result
    return {
        "ok": result.status == TaskStatus.SUCCEEDED,
        "task_id": str(result.task_id),
        "status": result.status,
        "goal": result.goal,
        "result": result.result,
        "error": result.error,
        "verified": any(
            event.type == "verification.completed" and event.data.get("ok")
            for event in _runtime.events.get(result.task_id, [])
        ),
        "events": [event.model_dump() for event in _runtime.events.get(result.task_id, [])],
    }


@router.get("/{task_id}")
def agent_status(task_id: UUID, owner_id: str = Depends(owner)) -> dict:
    with _lock:
        task = _tasks.get(str(task_id))
    if task is None or task.owner_id != owner_id:
        raise HTTPException(404, "agent run not found")
    return {
        "ok": True,
        "task_id": str(task.task_id),
        "status": task.status,
        "goal": task.goal,
        "result": task.result,
        "error": task.error,
        "events": [event.model_dump() for event in _runtime.events.get(task.task_id, [])],
    }


@router.post("/{task_id}/cancel")
def cancel_agent(task_id: UUID, owner_id: str = Depends(owner)) -> dict:
    with _lock:
        task = _tasks.get(str(task_id))
    if task is None or task.owner_id != owner_id:
        raise HTTPException(404, "agent run not found")
    try:
        _runtime.state_store.request_cancel(task_id)
    except Exception as exc:
        raise HTTPException(503, "agent control store unavailable") from exc
    return {"ok": True, "task_id": str(task_id), "status": "CANCEL_REQUESTED"}

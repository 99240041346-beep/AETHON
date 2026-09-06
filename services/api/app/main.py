import os
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from aethon.auth import current_owner, security
from aethon.schemas import TaskCreate, Task, ToolRequest
from aethon.store import TaskStore
from aethon.tools import ToolRegistry
from aethon.security import SafetyKernel
from aethon.model_router import ModelRouter
from aethon.memory_api import MemoryWriteRequest, MemorySearchRequest, MemoryDeleteRequest, MemoryMaintenanceRequest, write_memory, search_memory, delete_memory, plan_memory_maintenance
from aethon.memory_engine import MemorySecurityError


def build_task_store():
    """Select the durable runtime backend explicitly; never silently downgrade PostgreSQL."""
    database_url = os.getenv("AETHON_DATABASE_URL", "")
    if database_url.startswith(("postgres://", "postgresql://")):
        from aethon.postgres_task_store import PostgreSQLTaskStore
        return PostgreSQLTaskStore(database_url)
    return TaskStore()


app = FastAPI(title='AETHON API', version='0.1.0')
store = build_task_store()
tools = ToolRegistry()
safety = SafetyKernel()
model_router = ModelRouter()


def owner(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]) -> str:
    return current_owner(credentials)

@app.get('/health')
def health():
    return {'ok': True, 'service': 'aethon-api'}

@app.get('/ready')
def ready():
    scheduler = store.scheduler_status()
    persistence = scheduler.get('persistence', 'sqlite')
    if persistence == 'postgresql':
        ok = store.postgres.ping()
    else:
        ok = True
    return {'ok': ok, 'persistence': persistence, 'scheduler': scheduler}

@app.get('/v1/scheduler')
def scheduler_status(owner_id: str = Depends(owner)):
    return {'ok': True, **store.scheduler_status()}

@app.get('/v1/model/health')
def model_health():
    return {'ok': model_router.health(), 'provider': model_router.provider.name}

@app.get('/v1/tools')
def list_tools(): return tools.list()

@app.post('/v1/tools/execute')
def execute_tool(request: ToolRequest):
    spec = next((x for x in tools.list() if x.name == request.tool), None)
    if not spec: raise HTTPException(404, 'tool not found')
    decision = safety.authorize(spec.risk, spec.side_effects)
    if decision != 'ALLOW': raise HTTPException(403, f'action {decision.lower()}')
    return tools.execute(request)

@app.post('/v1/memory')
def create_memory(request: MemoryWriteRequest, owner_id: str = Depends(owner)):
    try: return write_memory(request, owner_id=owner_id)
    except MemorySecurityError as exc: raise HTTPException(400, str(exc)) from exc

@app.post('/v1/memory/search')
def search_memories(request: MemorySearchRequest, owner_id: str = Depends(owner)):
    try: return search_memory(request, owner_id=owner_id)
    except MemorySecurityError as exc: raise HTTPException(400, str(exc)) from exc

@app.post('/v1/memory/maintenance')
def memory_maintenance(request: MemoryMaintenanceRequest, owner_id: str = Depends(owner)):
    try: return plan_memory_maintenance(request, owner_id=owner_id)
    except MemorySecurityError as exc: raise HTTPException(400, str(exc)) from exc

@app.delete('/v1/memory/{memory_id}')
def remove_memory(memory_id: str, request: MemoryDeleteRequest, owner_id: str = Depends(owner)):
    try:
        deleted = delete_memory(memory_id, request, owner_id=owner_id)
        if not deleted: raise HTTPException(404, 'memory not found in authorized scope')
        return {'ok': True, 'memory_id': memory_id}
    except MemorySecurityError as exc: raise HTTPException(400, str(exc)) from exc

@app.post('/v1/tasks', response_model=Task)
def create_task(request: TaskCreate, owner_id: str = Depends(owner)):
    return store.create(request.model_copy(update={'owner_id': owner_id}))

@app.get('/v1/tasks/{task_id}', response_model=Task)
def get_task(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    return task

@app.get('/v1/tasks/{task_id}/events', response_model=list)
def get_events(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    return store.events(task_id)

@app.get('/v1/tasks/{task_id}/plan', response_model=dict)
def get_plan(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    snapshots = [event.data for event in store.events(task_id) if event.type in {'plan.created','plan.replanned'}]
    if not snapshots: raise HTTPException(404, 'plan not found')
    return snapshots[-1]

@app.get('/v1/tasks/{task_id}/audit', response_model=list)
def get_audit(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    return store.audit(task_id)

@app.post('/v1/tasks/{task_id}/pause', response_model=Task)
def pause_task(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    try: return store.pause(task_id)
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc

@app.post('/v1/tasks/{task_id}/resume', response_model=Task)
def resume_task(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    try: return store.resume(task_id)
    except ValueError as exc: raise HTTPException(409, str(exc)) from exc

@app.post('/v1/tasks/{task_id}/cancel', response_model=Task)
def cancel_task(task_id: UUID, owner_id: str = Depends(owner)):
    task = store.get(task_id)
    if not task or task.owner_id != owner_id: raise HTTPException(404, 'task not found')
    return store.cancel(task_id)

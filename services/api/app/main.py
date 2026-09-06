from fastapi import FastAPI, HTTPException
from uuid import UUID
from aethon.schemas import TaskCreate, Task, ToolRequest
from aethon.store import TaskStore
from aethon.tools import ToolRegistry
from aethon.security import SafetyKernel
from aethon.model_router import ModelRouter
from aethon.memory_api import MemoryWriteRequest, MemorySearchRequest, MemoryDeleteRequest, write_memory, search_memory, delete_memory
from aethon.memory_engine import MemorySecurityError

app = FastAPI(title='AETHON API', version='0.1.0')
store = TaskStore()
tools = ToolRegistry()
safety = SafetyKernel()
model_router = ModelRouter()

@app.get('/health')
def health():
    return {'ok': True, 'service': 'aethon-api'}

@app.get('/ready')
def ready():
    return {'ok': True, 'persistence': 'sqlite'}

@app.get('/v1/model/health')
def model_health():
    return {'ok': model_router.health(), 'provider': model_router.provider.name}

@app.get('/v1/tools')
def list_tools():
    return tools.list()

@app.post('/v1/tools/execute')
def execute_tool(request: ToolRequest):
    spec = next((x for x in tools.list() if x.name == request.tool), None)
    if not spec:
        raise HTTPException(404, 'tool not found')
    decision = safety.authorize(spec.risk, spec.side_effects)
    if decision != 'ALLOW':
        raise HTTPException(403, f'action {decision.lower()}')
    return tools.execute(request)

@app.post('/v1/memory')
def create_memory(request: MemoryWriteRequest):
    try:
        return write_memory(request)
    except MemorySecurityError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/v1/memory/search')
def search_memories(request: MemorySearchRequest):
    try:
        return search_memory(request)
    except MemorySecurityError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.delete('/v1/memory/{memory_id}')
def remove_memory(memory_id: str, request: MemoryDeleteRequest):
    try:
        deleted = delete_memory(memory_id, request)
        if not deleted:
            raise HTTPException(404, 'memory not found in authorized scope')
        return {'ok': True, 'memory_id': memory_id}
    except MemorySecurityError as exc:
        raise HTTPException(400, str(exc)) from exc

@app.post('/v1/tasks', response_model=Task)
def create_task(request: TaskCreate):
    return store.create(request)

@app.get('/v1/tasks/{task_id}', response_model=Task)
def get_task(task_id: UUID):
    task = store.get(task_id)
    if not task:
        raise HTTPException(404, 'task not found')
    return task

@app.get('/v1/tasks/{task_id}/events', response_model=list)
def get_events(task_id: UUID):
    if not store.get(task_id):
        raise HTTPException(404, 'task not found')
    return store.events(task_id)

@app.get('/v1/tasks/{task_id}/audit', response_model=list)
def get_audit(task_id: UUID):
    if not store.get(task_id):
        raise HTTPException(404, 'task not found')
    return store.audit(task_id)

@app.post('/v1/tasks/{task_id}/cancel', response_model=Task)
def cancel_task(task_id: UUID):
    task = store.cancel(task_id)
    if not task:
        raise HTTPException(404, 'task not found')
    return task

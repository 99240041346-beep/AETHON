from fastapi import FastAPI, HTTPException
from uuid import UUID
from aethon.schemas import TaskCreate, Task, ToolRequest
from aethon.store import TaskStore
from aethon.tools import ToolRegistry
from aethon.security import SafetyKernel

app = FastAPI(title='AETHON API', version='0.1.0')
store = TaskStore()
tools = ToolRegistry()
safety = SafetyKernel()

@app.get('/health')
def health():
    return {'ok': True, 'service': 'aethon-api'}

@app.get('/ready')
def ready():
    return {'ok': True, 'persistence': 'sqlite'}

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

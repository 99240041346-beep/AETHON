from uuid import UUID
from aethon.agent import AgentRuntime
from aethon.schemas import Event, Task, TaskCreate

class TaskStore:
    def __init__(self):
        self.tasks: dict[UUID, object] = {}
        self.runtime = AgentRuntime()
    def create(self, request: TaskCreate):
        task = __import__('aethon.schemas', fromlist=['Task']).Task(goal=request.goal, project_id=request.project_id, priority=request.priority)
        self.tasks[task.task_id] = task
        return self.runtime.run(task)
    def get(self, task_id: UUID): return self.tasks.get(task_id)
    def events(self, task_id: UUID) -> list[Event]: return self.runtime.events.get(task_id, [])

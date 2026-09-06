from uuid import UUID
from aethon.model_router import ModelRouter
from aethon.schemas import Event, Task, TaskStatus

class AgentRuntime:
    def __init__(self):
        self.models = ModelRouter()
        self.events: dict[UUID, list[Event]] = {}
    def run(self, task: Task) -> Task:
        self._transition(task, TaskStatus.PLANNING)
        self._transition(task, TaskStatus.EXECUTING)
        answer = self.models.generate(task.goal)
        self._transition(task, TaskStatus.VERIFYING)
        if not answer:
            task.status = TaskStatus.FAILED
            task.error = 'empty model result'
            self._event(task, 'task.failed', {'reason': task.error})
        else:
            task.result = answer
            self._transition(task, TaskStatus.SUCCEEDED)
        return task
    def _transition(self, task, status):
        task.status = status
        self._event(task, 'task.state_changed', {'status': status.value})
    def _event(self, task, typ, data):
        self.events.setdefault(task.task_id, []).append(Event(task_id=task.task_id, type=typ, data=data))

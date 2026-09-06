from uuid import UUID

from aethon.memory import InMemoryStore
from aethon.model_router import ModelRouter
from aethon.schemas import Event, Task, TaskStatus
from aethon.verification import BasicVerifier, Verifier
from aethon.web_runtime import WebAwareVerifier


class AgentRuntime:
    def __init__(self, verifier: Verifier | None = None, memory=None):
        self.models = ModelRouter()
        self.verifier = verifier or WebAwareVerifier(BasicVerifier())
        self.memory = memory or InMemoryStore()
        self.events: dict[UUID, list[Event]] = {}

    def run(self, task: Task) -> Task:
        self._transition(task, TaskStatus.PLANNING)
        self._audit(task, "task_started", {"project_id": task.project_id})

        context = self.memory.search(task.goal, project_id=task.project_id, limit=5)
        self._event(task, "memory.context_retrieved", {
            "project_id": task.project_id,
            "count": len(context),
            "memory_keys": [item.key for item in context],
        })

        self._transition(task, TaskStatus.EXECUTING)
        prompt = task.goal
        if context:
            prompt += "\nRelevant authorized project memory:\n" + "\n".join(
                f"- {item.key}: {item.value}" for item in context
            )
        answer = self.models.generate(prompt)
        self._transition(task, TaskStatus.VERIFYING)

        verification = self.verifier.verify(task.goal, answer)
        self._event(task, "verification.completed", {
            "ok": verification.ok,
            "reason": verification.reason,
            "evidence": verification.evidence,
        })
        self._audit(task, "verification", {"ok": verification.ok, "reason": verification.reason})

        if not verification.ok:
            task.status = TaskStatus.FAILED
            task.error = f"verification failed: {verification.reason}"
            self._event(task, "task.failed", {"reason": task.error})
            self._audit(task, "task_failed", {"reason": task.error})
        else:
            task.result = answer
            self.memory.put(f"task:{task.task_id}:result", answer, task.project_id)
            self._event(task, "memory.result_stored", {"project_id": task.project_id})
            self._transition(task, TaskStatus.SUCCEEDED)
            self._audit(task, "task_succeeded", {"verified": True})
        return task

    def _transition(self, task, status):
        task.status = status
        self._event(task, "task.state_changed", {"status": status.value})

    def _audit(self, task, action: str, data: dict):
        self._event(task, "audit." + action, data)

    def _event(self, task, typ, data):
        self.events.setdefault(task.task_id, []).append(
            Event(task_id=task.task_id, type=typ, data=data)
        )

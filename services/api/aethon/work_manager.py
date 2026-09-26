from __future__ import annotations

"""ASTRA project/task/automation primitives backed by the existing memory store."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class WorkItem:
    task_id: str
    owner_id: str
    project_id: str | None
    goal: str
    status: str = "queued"
    priority: int = 5
    attempts: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def transition(self, status: str) -> None:
        allowed = {
            "queued": {"running", "cancelled"},
            "running": {"waiting_confirmation", "completed", "failed", "cancelled"},
            "waiting_confirmation": {"running", "cancelled"},
            "failed": {"queued", "cancelled"},
            "completed": set(),
            "cancelled": set(),
        }
        if status not in allowed.get(self.status, set()):
            raise ValueError(f"invalid task transition: {self.status} -> {status}")
        self.status = status


@dataclass(frozen=True)
class AutomationSpec:
    automation_id: str
    owner_id: str
    goal: str
    interval_seconds: int
    enabled: bool = True


class WorkManager:
    def __init__(self) -> None:
        self._tasks: dict[str, WorkItem] = {}
        self._automations: dict[str, AutomationSpec] = {}

    def create_task(self, goal: str, owner_id: str, project_id: str | None = None, priority: int = 5) -> WorkItem:
        if not goal.strip() or not owner_id.strip():
            raise ValueError("goal and owner_id are required")
        if not 1 <= priority <= 10:
            raise ValueError("priority must be between 1 and 10")
        item = WorkItem(str(uuid4()), owner_id, project_id, goal.strip(), priority=priority)
        self._tasks[item.task_id] = item
        return item

    def get_task(self, task_id: str, owner_id: str) -> WorkItem:
        item = self._tasks.get(task_id)
        if item is None or item.owner_id != owner_id:
            raise KeyError("task not found")
        return item

    def schedule(self, goal: str, owner_id: str, interval_seconds: int, project_id: str | None = None) -> AutomationSpec:
        if interval_seconds < 60 or interval_seconds > 31_536_000:
            raise ValueError("interval_seconds must be between 60 and 31536000")
        spec = AutomationSpec(str(uuid4()), owner_id, goal.strip(), interval_seconds)
        self._automations[spec.automation_id] = spec
        return spec

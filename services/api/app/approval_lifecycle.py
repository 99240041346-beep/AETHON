from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID


class ApprovalLifecycleError(ValueError):
    """Raised when an approval transition is invalid or ambiguous."""


@dataclass(frozen=True)
class ApprovalRequest:
    task_id: str
    step_id: str
    tool: str
    risk: str
    side_effects: bool


@dataclass(frozen=True)
class ApprovalRecord:
    task_id: str
    step_id: str
    tool: str
    approved: bool
    approver: str


class ApprovalLifecycle:
    """Bounded, explicit approval state machine; it never executes a tool."""

    MAX_APPROVALS = 256
    MAX_FIELD = 256

    def __init__(self) -> None:
        self._pending: dict[tuple[str, str], ApprovalRequest] = {}
        self._approved: dict[tuple[str, str], ApprovalRecord] = {}

    @staticmethod
    def _key(task_id: str | UUID, step_id: str) -> tuple[str, str]:
        task = str(task_id).strip()
        step = str(step_id).strip()
        if not task or not step or len(task) > ApprovalLifecycle.MAX_FIELD or len(step) > ApprovalLifecycle.MAX_FIELD:
            raise ApprovalLifecycleError("invalid task or step identifier")
        return task, step

    def request(self, request: ApprovalRequest) -> ApprovalRequest:
        key = self._key(request.task_id, request.step_id)
        if len(self._pending) + len(self._approved) >= self.MAX_APPROVALS and key not in self._pending:
            raise ApprovalLifecycleError("approval budget exceeded")
        if not request.tool or len(request.tool) > self.MAX_FIELD:
            raise ApprovalLifecycleError("invalid tool")
        if not request.risk or len(request.risk) > self.MAX_FIELD:
            raise ApprovalLifecycleError("invalid risk")
        self._pending[key] = request
        return request

    def approve(self, task_id: str | UUID, step_id: str, approver: str) -> ApprovalRecord:
        key = self._key(task_id, step_id)
        approver = approver.strip()
        if not approver or len(approver) > self.MAX_FIELD:
            raise ApprovalLifecycleError("explicit approver is required")
        request = self._pending.get(key)
        if request is None:
            raise ApprovalLifecycleError("no pending approval for task step")
        record = ApprovalRecord(request.task_id, request.step_id, request.tool, True, approver)
        self._approved[key] = record
        self._pending.pop(key, None)
        return record

    def consume(self, task_id: str | UUID, step_id: str, tool: str) -> ApprovalRecord:
        key = self._key(task_id, step_id)
        record = self._approved.get(key)
        if record is None or record.tool != tool:
            raise ApprovalLifecycleError("explicit approval does not authorize this tool step")
        self._approved.pop(key, None)
        return record

    def pending(self, task_id: str | UUID, step_id: str) -> ApprovalRequest | None:
        return self._pending.get(self._key(task_id, step_id))

    def has_approval(self, task_id: str | UUID, step_id: str, tool: str) -> bool:
        key = self._key(task_id, step_id)
        record = self._approved.get(key)
        return bool(record and record.tool == tool)

    def clear(self, task_id: str | UUID, step_id: str) -> None:
        key = self._key(task_id, step_id)
        self._pending.pop(key, None)
        self._approved.pop(key, None)


__all__ = ["ApprovalLifecycle", "ApprovalLifecycleError", "ApprovalRecord", "ApprovalRequest"]

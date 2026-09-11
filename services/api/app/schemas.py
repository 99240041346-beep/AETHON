from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED='QUEUED'; PLANNING='PLANNING'; EXECUTING='EXECUTING'; VERIFYING='VERIFYING'; REPLANNING='REPLANNING'; AWAITING_APPROVAL='AWAITING_APPROVAL'; PAUSED='PAUSED'; SUCCEEDED='SUCCEEDED'; FAILED='FAILED'; BLOCKED='BLOCKED'; CANCELLED='CANCELLED'


class RiskClass(str, Enum):
    LOW='LOW'; MEDIUM='MEDIUM'; HIGH='HIGH'; CRITICAL='CRITICAL'


class TaskCreate(BaseModel):
    goal: str = Field(min_length=1, max_length=10000)
    project_id: str | None = None
    priority: int = Field(default=5, ge=1, le=10)
    owner_id: str = Field(default='local-dev', min_length=1, max_length=200)


class Task(BaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    goal: str
    project_id: str | None = None
    priority: int = 5
    owner_id: str = 'local-dev'
    status: TaskStatus = TaskStatus.QUEUED
    result: Any | None = None
    error: str | None = None


class Event(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk: RiskClass = RiskClass.LOW
    side_effects: bool = False
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    max_retries: int = Field(default=0, ge=0, le=5)
    authentication: str = 'owner'
    audit_required: bool = True


class ToolRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool
    output: Any | None = None
    error: str | None = None

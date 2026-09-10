from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.agent import AgentRuntime
from aethon.auth import current_owner, security
from aethon.schemas import Task, TaskStatus

router = APIRouter(prefix="/v1/assistant", tags=["assistant"])


class AssistantMode(str, Enum):
    CHAT = "CHAT"
    RESEARCH = "RESEARCH"
    CODING = "CODING"
    BROWSER = "BROWSER"
    COMPUTER = "COMPUTER"
    DOCUMENT = "DOCUMENT"
    DATA = "DATA"
    DEVICE = "DEVICE"
    WORKFLOW = "WORKFLOW"
    SCIENCE = "SCIENCE"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    SCHEDULING = "SCHEDULING"


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    language: str = Field(default="te-IN", min_length=2, max_length=16)
    session_id: str | None = Field(default=None, max_length=128)
    project_id: str | None = Field(default=None, max_length=200)
    mode: AssistantMode | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    autonomy: str = Field(default="bounded", max_length=32)


class AssistantResponse(BaseModel):
    ok: bool
    task_id: UUID
    mode: AssistantMode
    language: str
    session_id: str | None
    status: TaskStatus
    response: Any | None = None
    error: str | None = None
    capabilities_used: list[str] = Field(default_factory=list)
    verified: bool = False


def _owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


def _detect_mode(message: str, attachments: list[dict[str, Any]]) -> AssistantMode:
    text = message.casefold()
    if attachments:
        kinds = {str(item.get("kind", "")).casefold() for item in attachments}
        if "image" in kinds or "video" in kinds:
            return AssistantMode.COMPUTER if "screen" in text else AssistantMode.DOCUMENT
        if "file" in kinds or "document" in kinds:
            return AssistantMode.DOCUMENT
    rules = (
        (AssistantMode.CODING, ("code", "coding", "bug", "debug", "python", "javascript", "github", "build apk")),
        (AssistantMode.BROWSER, ("website", "browser", "open site", "search online", "web")),
        (AssistantMode.COMPUTER, ("computer", "desktop", "click", "type", "screen")),
        (AssistantMode.RESEARCH, ("research", "find out", "compare", "latest", "paper", "study")),
        (AssistantMode.SCIENCE, ("calculate", "experiment", "science", "math", "equation", "analysis")),
        (AssistantMode.EMAIL, ("email", "mail", "send message")),
        (AssistantMode.PHONE, ("call", "phone")),
        (AssistantMode.SCHEDULING, ("schedule", "meeting", "appointment", "calendar")),
        (AssistantMode.DEVICE, ("phone", "wifi", "bluetooth", "camera", "device", "notification")),
        (AssistantMode.DATA, ("csv", "spreadsheet", "data", "excel", "database")),
        (AssistantMode.DOCUMENT, ("document", "report", "presentation", "ppt", "pdf", "write")),
    )
    for mode, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return mode
    return AssistantMode.CHAT


@router.get("/capabilities")
def capabilities() -> dict[str, Any]:
    return {
        "ok": True,
        "assistant": "AETHON",
        "wake_phrase": "Hey Buddy",
        "identity": "Harsha's AETHON assistant",
        "languages": ["te-IN", "en-IN"],
        "modes": [mode.value for mode in AssistantMode],
        "autonomy": ["bounded", "approval_required", "observe_only"],
        "safety": "SafetyKernel + SafetyExecutionGate + ApprovalLifecycle",
        "architecture": "intent -> plan -> authorize -> execute -> verify -> remember",
        "note": "Capabilities without an installed adapter return bounded failure; the assistant never fabricates execution.",
    }


@router.post("/respond", response_model=AssistantResponse)
def respond(request: AssistantRequest, owner_id: str = Depends(_owner)) -> AssistantResponse:
    mode = request.mode or _detect_mode(request.message, request.attachments)
    task = Task(
        goal=request.message,
        project_id=request.project_id or request.session_id,
        owner_id=owner_id,
    )
    try:
        result = AgentRuntime().run(task)
    except Exception as exc:
        raise HTTPException(500, "assistant execution failed") from exc

    verified = result.status == TaskStatus.SUCCEEDED
    return AssistantResponse(
        ok=verified,
        task_id=result.task_id,
        mode=mode,
        language=request.language,
        session_id=request.session_id,
        status=result.status,
        response=result.result,
        error=result.error,
        capabilities_used=[mode.value],
        verified=verified,
    )

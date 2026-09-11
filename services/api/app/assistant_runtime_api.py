from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from app.assistant_runtime import AssistantRuntime
from app.language_service import detect_language

router = APIRouter(prefix="/v1/assistant/runtime", tags=["assistant-runtime"])
runtime = AssistantRuntime()


class RuntimeAssistantRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="te-IN", min_length=2, max_length=20)
    session_id: str | None = Field(default=None, max_length=100)
    project_id: str | None = Field(default=None, max_length=100)
    execute_tools: bool = True
    require_approval: bool = False


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


@router.post("/respond")
def runtime_respond(request: RuntimeAssistantRequest, owner_id: str = Depends(owner)) -> dict:
    profile = detect_language(request.text, request.language)
    language = profile.tts_locale
    try:
        result = runtime.run(
            owner_id=owner_id,
            session_id=request.session_id,
            text=request.text,
            language=language,
            project_id=request.project_id,
            execute_tools=request.execute_tools,
            require_approval=request.require_approval,
        )
    except PermissionError as exc:
        raise HTTPException(403, "session belongs to another owner") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(503, "assistant runtime unavailable") from exc

    return {
        "ok": result.error is None or result.tool_result is not None,
        "request_id": result.request_id,
        "session_id": result.session_id,
        "language": language,
        "mode": result.mode,
        "intent": result.intent.action,
        "response": result.response,
        "requires_confirmation": result.requires_confirmation,
        "action_authorized": result.action_authorized,
        "verified": result.verified,
        "error": result.error,
        "events": [
            {"type": event.type, "request_id": event.request_id, "data": event.data}
            for event in result.events
        ],
    }

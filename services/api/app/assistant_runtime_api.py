from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
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


def _result_payload(result, language: str) -> dict:
    return {
        "ok": result.error is None,
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

    return _result_payload(result, language)


@router.post("/stream")
async def runtime_stream(request: RuntimeAssistantRequest, owner_id: str = Depends(owner)) -> StreamingResponse:
    profile = detect_language(request.text, request.language)
    language = profile.tts_locale

    async def events():
        yield "event: started\ndata: " + json.dumps({"status": "started", "language": language}) + "\n\n"
        try:
            result = await asyncio.to_thread(
                runtime.run,
                owner_id=owner_id,
                session_id=request.session_id,
                text=request.text,
                language=language,
                project_id=request.project_id,
                execute_tools=request.execute_tools,
                require_approval=request.require_approval,
            )
            for event in result.events:
                payload = {"type": event.type, "request_id": event.request_id, "data": event.data}
                yield "event: progress\ndata: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
            yield "event: completed\ndata: " + json.dumps(_result_payload(result, language), ensure_ascii=False) + "\n\n"
        except PermissionError:
            yield "event: error\ndata: " + json.dumps({"error": "session belongs to another owner"}) + "\n\n"
        except ValueError as exc:
            yield "event: error\ndata: " + json.dumps({"error": str(exc)}) + "\n\n"
        except Exception:
            yield "event: error\ndata: " + json.dumps({"error": "assistant runtime unavailable"}) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

from __future__ import annotations

import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from app.assistant_runtime import AssistantRuntime, RuntimeEvent
from app.language_service import detect_language
from app.attachment_store import create_attachment, get_attachment

router = APIRouter(prefix="/v1/assistant/runtime", tags=["assistant-runtime"])
runtime = AssistantRuntime()


class RuntimeAssistantRequest(BaseModel):
    model_config = {"extra": "forbid"}

    text: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="te-IN", min_length=2, max_length=20)
    session_id: str | None = Field(default=None, max_length=100)
    project_id: str | None = Field(default=None, max_length=100)
    execute_tools: bool = True
    require_approval: bool = False
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)


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
        "visualization": getattr(result, "visualization", None),
        "events": [
            {"type": event.type, "request_id": event.request_id, "data": event.data}
            for event in result.events
        ],
    }


def _progress_payload(event: RuntimeEvent) -> dict:
    return {"type": event.type, "request_id": event.request_id, "data": event.data}

@router.post("/attachments")
async def upload_attachment(file: UploadFile = File(...), owner_id: str = Depends(owner)) -> dict:
    try:
        raw = await file.read()
        item = create_attachment(
            owner_id=owner_id,
            filename=file.filename or "attachment",
            media_type=file.content_type or "application/octet-stream",
            raw=raw,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "ok": True,
        "attachment_id": item.attachment_id,
        "filename": item.filename,
        "media_type": item.media_type,
        "size": item.size,
        "sha256": item.sha256,
        "kind": item.kind,
        "text_available": item.text is not None,
    }

@router.get("/attachments/{attachment_id}")
def attachment_info(attachment_id: str, owner_id: str = Depends(owner)) -> dict:
    item = get_attachment(attachment_id, owner_id)
    if item is None:
        raise HTTPException(404, "attachment not found")
    return {"ok": True, "attachment_id": item.attachment_id, "filename": item.filename,
            "media_type": item.media_type, "size": item.size, "sha256": item.sha256,
            "kind": item.kind, "text_available": item.text is not None}


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
            attachment_ids=request.attachment_ids,
            request_id=str(uuid4()),
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
    request_id = str(uuid4())

    async def events():
        queue: asyncio.Queue[RuntimeEvent] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def on_event(event: RuntimeEvent) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, event)

        yield "event: started\ndata: " + json.dumps(
            {"status": "started", "request_id": request_id, "language": language},
            ensure_ascii=False,
        ) + "\n\n"

        task = asyncio.create_task(asyncio.to_thread(
            runtime.run,
            owner_id=owner_id,
            session_id=request.session_id,
            text=request.text,
            language=language,
            project_id=request.project_id,
            execute_tools=request.execute_tools,
            require_approval=request.require_approval,
            attachment_ids=request.attachment_ids,
            request_id=request_id,
            event_callback=on_event,
        ))

        try:
            while not task.done() or not queue.empty():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    continue
                yield "event: progress\ndata: " + json.dumps(
                    _progress_payload(event), ensure_ascii=False
                ) + "\n\n"

            result = await task
            yield "event: completed\ndata: " + json.dumps(
                _result_payload(result, language), ensure_ascii=False
            ) + "\n\n"
        except PermissionError:
            if not task.done():
                task.cancel()
            yield "event: error\ndata: " + json.dumps(
                {"request_id": request_id, "error": "session belongs to another owner"},
                ensure_ascii=False,
            ) + "\n\n"
        except ValueError as exc:
            yield "event: error\ndata: " + json.dumps(
                {"request_id": request_id, "error": str(exc)}, ensure_ascii=False
            ) + "\n\n"
        except Exception:
            yield "event: error\ndata: " + json.dumps(
                {"request_id": request_id, "error": "assistant runtime unavailable"},
                ensure_ascii=False,
            ) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

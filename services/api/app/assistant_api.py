from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.assistant_orchestrator import AssistantMode, AssistantOrchestrator
from aethon.auth import current_owner, security
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.model_router import ModelRouter
from aethon.schemas import RiskClass
from aethon.security import SafetyKernel
from app.assistant_repository import AssistantRepository
from app.language_service import detect_language

router = APIRouter(prefix="/v1/assistant", tags=["assistant"])
orchestrator = AssistantOrchestrator()
model_router = ModelRouter()
safety_gate = SafetyExecutionGate(SafetyKernel())
repository = AssistantRepository()


class AssistantRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="te-IN", min_length=2, max_length=20)
    session_id: str | None = Field(default=None, max_length=100)
    project_id: str | None = Field(default=None, max_length=100)


class AssistantResponse(BaseModel):
    ok: bool
    session_id: str
    language: str
    mode: AssistantMode
    intent: str | None
    response: str
    requires_confirmation: bool
    action_authorized: bool = False


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


def _chat_prompt(request: AssistantRequest, owner_id: str, session_id: str, language: str) -> str:
    instruction = (
        "Respond naturally in Telugu. Telugu-English mixed input is allowed; preserve useful English technical terms."
        if language.startswith("te") else
        "Respond naturally in English."
        if language.startswith("en") else
        "Respond naturally in the user's language when possible."
    )
    return (
        "You are AETHON, a bounded personal AI assistant. "
        f"Owner: {owner_id}. Session: {session_id}. {instruction} "
        "Be useful and concise. Never claim an external action occurred unless an authorized tool verified it. "
        f"User: {request.text}"
    )


@router.post("/respond", response_model=AssistantResponse)
def respond(request: AssistantRequest, owner_id: str = Depends(owner)) -> AssistantResponse:
    session_id = request.session_id or str(uuid4())
    profile = detect_language(request.text, request.language)
    language = profile.tts_locale
    try:
        repository.ensure_session(session_id, owner_id, language, request.project_id)
        repository.add_message(session_id, owner_id, "user", request.text, language)
    except Exception as exc:
        raise HTTPException(503, "assistant persistence unavailable") from exc

    intent = orchestrator.classify(request.text)
    if intent.mode is AssistantMode.CHAT:
        try:
            safety_gate.authorize(RiskClass.LOW, side_effects=False)
            if model_router.provider.name == "deterministic":
                response = orchestrator.respond(request.text, language=language).text
            else:
                response = model_router.generate(_chat_prompt(request, owner_id, session_id, language))
        except ExecutionAuthorizationError as exc:
            raise HTTPException(403, "assistant request blocked by safety policy") from exc
        except Exception:
            response = orchestrator.respond(request.text, language=language).text
    else:
        response = orchestrator.respond(request.text, language=language).text

    try:
        repository.add_message(session_id, owner_id, "assistant", response, language,
                               intent=intent.mode.value, action=intent.action,
                               status="READY", metadata={"requires_confirmation": intent.requires_confirmation})
    except Exception as exc:
        raise HTTPException(503, "assistant response persistence failed") from exc

    return AssistantResponse(
        ok=True,
        session_id=session_id,
        language=language,
        mode=intent.mode,
        intent=intent.action,
        response=response,
        requires_confirmation=intent.requires_confirmation,
        action_authorized=False,
    )


@router.get("/sessions")
def sessions(limit: int = 50, owner_id: str = Depends(owner)) -> list[dict]:
    try:
        return repository.sessions(owner_id, limit)
    except Exception as exc:
        raise HTTPException(503, "assistant persistence unavailable") from exc


@router.get("/sessions/{session_id}")
def session(session_id: str, owner_id: str = Depends(owner)) -> dict:
    try:
        result = repository.session(session_id, owner_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid session id") from exc
    except Exception as exc:
        raise HTTPException(503, "assistant persistence unavailable") from exc
    if result is None:
        raise HTTPException(404, "session not found")
    return result


@router.get("/sessions/{session_id}/messages")
def history(session_id: str, limit: int = 50, owner_id: str = Depends(owner)) -> list[dict]:
    try:
        return repository.history(session_id, owner_id, limit)
    except ValueError as exc:
        raise HTTPException(400, "invalid session id") from exc
    except Exception as exc:
        raise HTTPException(503, "assistant persistence unavailable") from exc


@router.delete("/sessions/{session_id}")
def archive_session(session_id: str, owner_id: str = Depends(owner)) -> dict:
    try:
        archived = repository.archive_session(session_id, owner_id)
    except ValueError as exc:
        raise HTTPException(400, "invalid session id") from exc
    except Exception as exc:
        raise HTTPException(503, "assistant persistence unavailable") from exc
    if not archived:
        raise HTTPException(404, "session not found")
    return {"ok": True, "session_id": session_id, "archived": True}

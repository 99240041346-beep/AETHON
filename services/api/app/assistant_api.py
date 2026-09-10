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

router = APIRouter(prefix="/v1/assistant", tags=["assistant"])
orchestrator = AssistantOrchestrator()
model_router = ModelRouter()
safety_gate = SafetyExecutionGate(SafetyKernel())


class AssistantRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="te-IN", min_length=2, max_length=20)
    session_id: str | None = Field(default=None, max_length=100)


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


def _chat_prompt(request: AssistantRequest, owner_id: str, session_id: str) -> str:
    language = request.language.lower()
    if language.startswith("te"):
        instruction = "Respond naturally in Telugu. Telugu-English mixed input is allowed; preserve useful English technical terms."
    elif language.startswith("en"):
        instruction = "Respond naturally in English."
    else:
        instruction = "Respond naturally in the user's language when possible."
    return (
        "You are AETHON, a bounded personal AI assistant. "
        f"Owner: {owner_id}. Session: {session_id}. {instruction} "
        "Be useful and concise. Never claim an external action occurred unless an authorized tool verified it. "
        f"User: {request.text}"
    )


@router.post("/respond", response_model=AssistantResponse)
def respond(request: AssistantRequest, owner_id: str = Depends(owner)) -> AssistantResponse:
    session_id = request.session_id or str(uuid4())
    intent = orchestrator.classify(request.text)
    if intent.mode is AssistantMode.CHAT:
        try:
            safety_gate.authorize(RiskClass.LOW, side_effects=False)
            if model_router.provider.name == "deterministic":
                response = orchestrator.respond(request.text, language=request.language).text
            else:
                response = model_router.generate(_chat_prompt(request, owner_id, session_id))
        except ExecutionAuthorizationError as exc:
            raise HTTPException(403, "assistant request blocked by safety policy") from exc
        except Exception:
            response = orchestrator.respond(request.text, language=request.language).text
    else:
        response = orchestrator.respond(request.text, language=request.language).text
    return AssistantResponse(
        ok=True,
        session_id=session_id,
        language=request.language,
        mode=intent.mode,
        intent=intent.action,
        response=response,
        requires_confirmation=intent.requires_confirmation,
        action_authorized=False,
    )

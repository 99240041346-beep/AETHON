from __future__ import annotations

import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from aethon.model_router import ModelRouter
from aethon.security import SafetyKernel
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate

router = APIRouter(prefix="/v1/voice", tags=["voice"])
model_router = ModelRouter()
safety_gate = SafetyExecutionGate(SafetyKernel())


class VoiceRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="te-IN", min_length=2, max_length=20)
    session_id: str | None = Field(default=None, max_length=100)


class VoiceResponse(BaseModel):
    ok: bool
    session_id: str
    language: str
    transcript: str
    response: str
    provider: str
    action_authorized: bool = False


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


def _language_instruction(language: str) -> str:
    normalized = language.lower()
    if normalized.startswith("te"):
        return "Respond naturally in Telugu. Telugu-English mixed input is allowed; preserve useful English technical terms."
    if normalized.startswith("en"):
        return "Respond naturally in English."
    return "Respond in the user's language when possible; keep technical terms clear."


@router.post("/respond", response_model=VoiceResponse)
def respond(request: VoiceRequest, owner_id: str = Depends(owner)) -> VoiceResponse:
    # Voice I/O is never an authorization mechanism. The safety gate is evaluated
    # for the conversational operation and no device tool is executed here.
    try:
        safety_gate.authorize(risk="LOW", side_effects=False)  # type: ignore[arg-type]
    except (ExecutionAuthorizationError, ValueError) as exc:
        raise HTTPException(403, "voice request blocked by safety policy") from exc

    session_id = request.session_id or str(uuid4())
    prompt = (
        "You are AETHON, a bounded personal AI assistant. "
        f"Owner: {owner_id}. Session: {session_id}. "
        f"{_language_instruction(request.language)} "
        "Answer concisely and do not claim an external action occurred unless an authorized tool actually verified it. "
        f"User said: {request.transcript}"
    )
    try:
        response = model_router.generate(prompt)
    except Exception as exc:
        # Deterministic fallback keeps voice interaction available when a model is unavailable.
        response = f"నేను విన్నాను: {request.transcript}" if request.language.lower().startswith("te") else f"I heard you: {request.transcript}"
        provider = "deterministic-fallback"
    else:
        provider = model_router.provider.name
    return VoiceResponse(
        ok=True,
        session_id=session_id,
        language=request.language,
        transcript=request.transcript,
        response=response,
        provider=provider,
        action_authorized=False,
    )

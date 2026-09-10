from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.assistant_command_bridge import AssistantCommandBridge
from aethon.auth import current_owner, security
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.model_router import ModelRouter
from aethon.schemas import RiskClass
from aethon.security import SafetyKernel

router = APIRouter(prefix="/v1/voice", tags=["voice"])
model_router = ModelRouter()
safety_gate = SafetyExecutionGate(SafetyKernel())
command_bridge = AssistantCommandBridge()


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
    action: str | None = None
    action_arguments: dict[str, str] = Field(default_factory=dict)


def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)


def _language_instruction(language: str) -> str:
    normalized = language.lower()
    if normalized.startswith("te"):
        return "Respond naturally in Telugu. Telugu-English mixed input is allowed; preserve useful English technical terms."
    if normalized.startswith("en"):
        return "Respond naturally in English."
    return "Respond in the user's language when possible; keep technical terms clear."


def _deterministic_fallback(request: VoiceRequest) -> str:
    if request.language.lower().startswith("te"):
        return f"నేను విన్నాను: {request.transcript}"
    return f"I heard you: {request.transcript}"


def _action_reply(request: VoiceRequest, app: str) -> str:
    if request.language.lower().startswith("te"):
        return f"సరే Harsha, {app} ఓపెన్ చేస్తున్నాను."
    return f"Okay Harsha, opening {app}."


@router.post("/respond", response_model=VoiceResponse)
def respond(request: VoiceRequest, owner_id: str = Depends(owner)) -> VoiceResponse:
    try:
        safety_gate.authorize(RiskClass.LOW, side_effects=False)
    except ExecutionAuthorizationError as exc:
        raise HTTPException(403, "voice request blocked by safety policy") from exc

    session_id = request.session_id or str(uuid4())
    intent = command_bridge.classify(request.transcript, language=request.language)
    if intent is not None and intent.action == "android.open_app":
        return VoiceResponse(
            ok=True,
            session_id=session_id,
            language=request.language,
            transcript=request.transcript,
            response=_action_reply(request, intent.arguments["app"]),
            provider="command-bridge",
            action_authorized=True,
            action=intent.action,
            action_arguments={k: str(v) for k, v in intent.arguments.items()},
        )

    prompt = (
        "You are AETHON, a bounded personal AI assistant. "
        f"Owner: {owner_id}. Session: {session_id}. "
        f"{_language_instruction(request.language)} "
        "Answer concisely. Never claim an external action occurred unless an authorized tool actually verified it. "
        f"User said: {request.transcript}"
    )

    try:
        provider_name = model_router.provider.name
        if provider_name == "deterministic":
            response = _deterministic_fallback(request)
            provider = "deterministic-fallback"
        else:
            response = model_router.generate(prompt)
            provider = provider_name
    except Exception:
        response = _deterministic_fallback(request)
        provider = "deterministic-fallback"

    return VoiceResponse(
        ok=True,
        session_id=session_id,
        language=request.language,
        transcript=request.transcript,
        response=response,
        provider=provider,
        action_authorized=False,
    )

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
from app.language_service import action_ack, deterministic_ack, detect_language, language_instruction
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
    action_package: str | None = None

def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)

def _action_reply(request: VoiceRequest, app: str, language: str) -> str:
    return action_ack(detect_language(request.transcript, language), app)

@router.post("/respond", response_model=VoiceResponse)
def respond(request: VoiceRequest, owner_id: str = Depends(owner)) -> VoiceResponse:
    try: safety_gate.authorize(RiskClass.LOW, side_effects=False)
    except ExecutionAuthorizationError as exc: raise HTTPException(403, "voice request blocked by safety policy") from exc
    profile = detect_language(request.transcript, request.language)
    session_id = request.session_id or str(uuid4())
    intent = command_bridge.classify(request.transcript, language=profile.tts_locale)
    if intent is not None and intent.action == "android.open_app":
        return VoiceResponse(ok=True, session_id=session_id, language=profile.tts_locale, transcript=request.transcript,
            response=_action_reply(request, intent.arguments["app"], profile.code), provider="command-bridge", action_authorized=True,
            action=intent.action, action_package=str(intent.arguments["package"]))
    prompt = ("You are AETHON, a bounded personal AI assistant. " f"Owner: {owner_id}. Session: {session_id}. "
              f"{language_instruction(profile)} "
              "Never claim an external action occurred unless an authorized tool actually verified it. "
              f"User said: {request.transcript}")
    try:
        provider_name = model_router.provider.name
        if provider_name == "deterministic": response, provider = deterministic_ack(profile, request.transcript), "deterministic-fallback"
        else: response, provider = model_router.generate(prompt), provider_name
    except Exception: response, provider = deterministic_ack(profile, request.transcript), "deterministic-fallback"
    return VoiceResponse(ok=True, session_id=session_id, language=profile.tts_locale, transcript=request.transcript,
        response=response, provider=provider, action_authorized=False)

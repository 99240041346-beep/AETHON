from __future__ import annotations

import secrets
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.assistant_orchestrator import AssistantMode, AssistantOrchestrator
from aethon.android_command_transport import AndroidCommandTransport, CommandTransportError
from aethon.auth import current_owner, security
from aethon.device_gateway import GatewayError
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.model_router import ModelRouter
from aethon.schemas import RiskClass
from aethon.security import SafetyKernel
from app.assistant_repository import AssistantRepository
from app.android_workflow import AndroidWorkflowPlanner
from app.language_service import detect_language
from app.device_gateway_api import gateway

router = APIRouter(prefix="/v1/assistant", tags=["assistant"])
orchestrator = AssistantOrchestrator()
model_router = ModelRouter()
safety_gate = SafetyExecutionGate(SafetyKernel())
repository = AssistantRepository()
transport = AndroidCommandTransport()
workflow_planner = AndroidWorkflowPlanner()

class AssistantRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    language: str = Field(default="te-IN", min_length=2, max_length=20)
    session_id: str | None = Field(default=None, max_length=100)
    project_id: str | None = Field(default=None, max_length=100)

class DeviceActionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    device_id: str = Field(min_length=1, max_length=128)
    approval: bool = False
    ttl_seconds: float = Field(default=15, gt=0, le=30)

class DeviceWorkflowRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    device_id: str = Field(min_length=1, max_length=128)
    approval: bool = False
    ttl_seconds: float = Field(default=15, gt=0, le=30)

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
    instruction = "Respond naturally in Telugu. Telugu-English mixed input is allowed; preserve useful English technical terms." if language.startswith("te") else "Respond naturally in English." if language.startswith("en") else "Respond naturally in the user's language when possible."
    return f"You are AETHON, a bounded personal AI assistant. Owner: {owner_id}. Session: {session_id}. {instruction} Be useful and concise. Never claim an external action occurred unless an authorized tool verified it. User: {request.text}"

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
            response = orchestrator.respond(request.text, language=language).text if model_router.provider.name == "deterministic" else model_router.generate(_chat_prompt(request, owner_id, session_id, language))
        except ExecutionAuthorizationError as exc:
            raise HTTPException(403, "assistant request blocked by safety policy") from exc
        except Exception:
            response = orchestrator.respond(request.text, language=language).text
    else:
        response = orchestrator.respond(request.text, language=language).text
    try:
        repository.add_message(session_id, owner_id, "assistant", response, language, intent=intent.mode.value, action=intent.action, status="READY", metadata={"requires_confirmation": intent.requires_confirmation})
    except Exception as exc:
        raise HTTPException(503, "assistant response persistence failed") from exc
    return AssistantResponse(ok=True, session_id=session_id, language=language, mode=intent.mode, intent=intent.action, response=response, requires_confirmation=intent.requires_confirmation, action_authorized=False)

@router.post("/device-action")
def device_action(request: DeviceActionRequest, owner_id: str = Depends(owner)) -> dict:
    intent = orchestrator.classify(request.text)
    capability_map = {"android.open_app": "OPEN_APP", "android.screen_click": "SCREEN_CLICK", "android.screen_scroll": "SCREEN_SCROLL", "android.screen_text": "SCREEN_TEXT", "android.screen_back": "SCREEN_BACK"}
    capability = capability_map.get(intent.action or "")
    if capability is None:
        raise HTTPException(400, "request is not a supported Android action")
    if not request.approval:
        return {"ok": True, "authorized": False, "requires_confirmation": True, "intent": intent.action, "capability": capability, "message": "Explicit approval is required before sending this device action."}
    try:
        device = gateway.status(device_id=request.device_id, owner_id=owner_id)
    except GatewayError as exc:
        raise HTTPException(404, str(exc)) from exc
    if capability not in set(device["capabilities"]):
        raise HTTPException(403, "device capability not granted")
    try:
        command = transport.enqueue(owner_id=owner_id, device_id=request.device_id, capability=capability, arguments=intent.arguments, nonce=secrets.token_urlsafe(24), approved=True, ttl_seconds=request.ttl_seconds)
    except CommandTransportError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "authorized": True, "requires_confirmation": False, "intent": intent.action, "capability": capability, "command_id": command.command_id, "status": command.status, "expires_at": command.expires_at}

@router.post("/device-workflow")
def device_workflow(request: DeviceWorkflowRequest, owner_id: str = Depends(owner)) -> dict:
    try:
        steps = workflow_planner.encode(workflow_planner.plan(request.text))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not request.approval:
        return {"ok": True, "authorized": False, "requires_confirmation": True, "step_count": len(steps), "workflow": steps, "message": "Explicit approval is required before executing this Android workflow."}
    try:
        device = gateway.status(device_id=request.device_id, owner_id=owner_id)
    except GatewayError as exc:
        raise HTTPException(404, str(exc)) from exc
    if any(step["capability"] not in set(device["capabilities"]) for step in steps):
        raise HTTPException(403, "one or more workflow capabilities are not granted on this device")
    workflow_id = str(uuid4())
    workflow = {"id": workflow_id, "steps": steps, "next_index": 1, "max_retries": 1, "state": "RUNNING"}
    first = steps[0]
    try:
        command = transport.enqueue(owner_id=owner_id, device_id=request.device_id, capability=first["capability"], arguments={**first["arguments"], "_workflow": workflow}, nonce=secrets.token_urlsafe(24), approved=True, ttl_seconds=request.ttl_seconds)
    except CommandTransportError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "authorized": True, "workflow_started": True, "workflow_id": workflow_id, "step_index": 0, "step_count": len(steps), "command_id": command.command_id, "capability": command.capability, "status": command.status}

@router.get("/android-workflows/{workflow_id}")
def workflow_status(workflow_id: str, owner_id: str = Depends(owner)) -> dict:
    workflow = transport.workflow(workflow_id=workflow_id, owner_id=owner_id)
    if workflow is None:
        raise HTTPException(404, "workflow not found")
    return {"ok": True, **workflow}

@router.post("/android-workflows/{workflow_id}/pause")
def pause_workflow(workflow_id: str, owner_id: str = Depends(owner)) -> dict:
    try:
        workflow = transport.set_workflow_state(workflow_id=workflow_id, owner_id=owner_id, state="PAUSED")
    except CommandTransportError as exc:
        raise HTTPException(400, str(exc)) from exc
    if workflow is None:
        raise HTTPException(404, "workflow not found")
    return {"ok": True, "workflow": workflow, "state": "PAUSED"}

@router.post("/android-workflows/{workflow_id}/cancel")
def cancel_workflow(workflow_id: str, owner_id: str = Depends(owner)) -> dict:
    try:
        workflow = transport.set_workflow_state(workflow_id=workflow_id, owner_id=owner_id, state="CANCELLED")
    except CommandTransportError as exc:
        raise HTTPException(400, str(exc)) from exc
    if workflow is None:
        raise HTTPException(404, "workflow not found")
    return {"ok": True, "workflow": workflow, "state": "CANCELLED"}

@router.post("/android-workflows/{workflow_id}/resume")
def resume_workflow(workflow_id: str, owner_id: str = Depends(owner)) -> dict:
    try:
        current = transport.workflow(workflow_id=workflow_id, owner_id=owner_id)
        if current is None or not isinstance(current.get("workflow"), dict):
            raise HTTPException(404, "workflow not found")
        wf = current["workflow"]
        if wf.get("state", "RUNNING") != "PAUSED":
            raise HTTPException(409, f"workflow is {str(wf.get('state', 'RUNNING')).lower()}, not paused")
        workflow = transport.set_workflow_state(workflow_id=workflow_id, owner_id=owner_id, state="RUNNING")
        if workflow is None:
            raise HTTPException(404, "workflow not found")
        latest = transport.get(command_id=workflow["command_id"], owner_id=owner_id)
        resumed_workflow = workflow.get("workflow") or {}
        steps = resumed_workflow.get("steps", [])
        next_index = resumed_workflow.get("next_index")
        next_command = None
        if not isinstance(steps, list) or not isinstance(next_index, int):
            raise HTTPException(409, "workflow state is invalid")

        # The latest ACCEPTED command may be unclaimed or in-flight. It already
        # represents the durable next step, so resume must not duplicate it.
        if latest and latest.get("status") == "ACCEPTED":
            return {"ok": True, "workflow": workflow, "state": "RUNNING", "next": None, "message": "Workflow resumed; existing step remains queued or in flight."}

        if latest and latest.get("status") == "COMPLETED":
            index = next_index
            if index >= len(steps):
                workflow = transport.set_workflow_state(workflow_id=workflow_id, owner_id=owner_id, state="COMPLETED") or workflow
            else:
                pending = transport.workflow_step_pending(workflow_id=workflow_id, owner_id=owner_id, step_index=index)
                if pending:
                    next_command = {"command_id": pending["command_id"], "step_index": index, "step_count": len(steps), "capability": pending["capability"], "status": pending["status"]}
                else:
                    step = steps[index]
                    capability = step.get("capability") if isinstance(step, dict) else None
                    arguments = step.get("arguments", {}) if isinstance(step, dict) else {}
                    if capability not in {"SCREEN_READ", "SCREEN_CLICK", "SCREEN_SCROLL", "SCREEN_TEXT", "SCREEN_BACK", "APP_LIST", "DEVICE_INFO", "NETWORK_STATUS", "BATTERY_READ", "VOLUME_READ", "OPEN_APP", "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_STOP", "VOLUME_SET", "FLASHLIGHT_ON", "FLASHLIGHT_OFF", "SCREEN_CAPTURE"} or not isinstance(arguments, dict):
                        raise HTTPException(409, "workflow contains an invalid next capability")
                    next_workflow = {**resumed_workflow, "next_index": index + 1, "state": "RUNNING"}
                    queued = transport.enqueue(owner_id=owner_id, device_id=latest["device_id"], capability=capability, arguments={**arguments, "_workflow": next_workflow}, nonce=secrets.token_urlsafe(24), approved=True, ttl_seconds=15)
                    next_command = {"command_id": queued.command_id, "step_index": index, "step_count": len(steps), "capability": capability, "status": queued.status}
        elif latest and latest.get("status") in {"EXPIRED", "REJECTED"}:
            index = max(0, next_index - 1)
            if index < len(steps):
                decision_workflow = {**resumed_workflow, "state": "RUNNING"}
                decision = __import__("app.android_workflow_recovery", fromlist=["decide_retry"]).decide_retry(decision_workflow, step_index=index, success=False, verified=False)
                if decision.retry:
                    from app.android_workflow_recovery import with_attempt
                    retry_workflow = with_attempt(decision_workflow, step_index=index, attempt=decision.attempt)
                    pending = transport.workflow_step_pending(workflow_id=workflow_id, owner_id=owner_id, step_index=index)
                    if pending:
                        next_command = {"command_id": pending["command_id"], "step_index": index, "step_count": len(steps), "capability": pending["capability"], "status": pending["status"]}
                    else:
                        step = steps[index]
                        capability = step.get("capability") if isinstance(step, dict) else None
                        arguments = step.get("arguments", {}) if isinstance(step, dict) else {}
                        if capability not in {"SCREEN_READ", "SCREEN_CLICK", "SCREEN_SCROLL", "SCREEN_TEXT", "SCREEN_BACK", "OPEN_APP"} or not isinstance(arguments, dict):
                            raise HTTPException(409, "workflow retry contains an invalid capability")
                        queued = transport.enqueue(owner_id=owner_id, device_id=latest["device_id"], capability=capability, arguments={**arguments, "_workflow": retry_workflow}, nonce=secrets.token_urlsafe(24), approved=True, ttl_seconds=15)
                        next_command = {"command_id": queued.command_id, "step_index": index, "step_count": len(steps), "capability": capability, "status": queued.status}
                else:
                    workflow = transport.set_workflow_state(workflow_id=workflow_id, owner_id=owner_id, state="FAILED") or workflow
        return {"ok": True, "workflow": workflow, "state": workflow.get("workflow", {}).get("state", "RUNNING"), "next": next_command, "message": "Workflow resumed."}
    except CommandTransportError as exc:
        raise HTTPException(400, str(exc)) from exc

@router.get("/sessions")
def sessions(limit: int = 50, owner_id: str = Depends(owner)) -> list[dict]:
    try: return repository.sessions(owner_id, limit)
    except Exception as exc: raise HTTPException(503, "assistant persistence unavailable") from exc

@router.get("/sessions/{session_id}")
def session(session_id: str, owner_id: str = Depends(owner)) -> dict:
    try: result = repository.session(session_id, owner_id)
    except ValueError as exc: raise HTTPException(400, "invalid session id") from exc
    except Exception as exc: raise HTTPException(503, "assistant persistence unavailable") from exc
    if result is None: raise HTTPException(404, "session not found")
    return result

@router.get("/sessions/{session_id}/messages")
def history(session_id: str, limit: int = 50, owner_id: str = Depends(owner)) -> list[dict]:
    try: return repository.history(session_id, owner_id, limit)
    except ValueError as exc: raise HTTPException(400, "invalid session id") from exc

@router.delete("/sessions/{session_id}")
def archive_session(session_id: str, owner_id: str = Depends(owner)) -> dict:
    try: archived = repository.archive_session(session_id, owner_id)
    except ValueError as exc: raise HTTPException(400, "invalid session id") from exc
    except Exception as exc: raise HTTPException(503, "assistant persistence unavailable") from exc
    if not archived: raise HTTPException(404, "session not found")
    return {"ok": True, "session_id": session_id, "archived": True}

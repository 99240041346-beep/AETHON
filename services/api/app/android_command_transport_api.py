from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from aethon.android_command_transport import AndroidCommandTransport, CommandTransportError
from aethon.auth import current_owner, security
from aethon.device_gateway import GatewayError
from app.android_workflow import AndroidWorkflowPlanner
from app.android_workflow_recovery import decide_retry, with_attempt

router = APIRouter(prefix="/v1/android/commands", tags=["android-command-transport"])
_ALLOWED = {"SCREEN_READ", "SCREEN_CLICK", "SCREEN_SCROLL", "SCREEN_TEXT", "SCREEN_BACK", "APP_LIST", "DEVICE_INFO", "NETWORK_STATUS", "BATTERY_READ", "VOLUME_READ", "OPEN_APP", "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_STOP", "VOLUME_SET", "FLASHLIGHT_ON", "FLASHLIGHT_OFF", "SCREEN_CAPTURE"}
_READ_ONLY = {"SCREEN_READ", "APP_LIST", "DEVICE_INFO", "NETWORK_STATUS", "BATTERY_READ", "VOLUME_READ"}

class EnqueueRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    capability: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any] = Field(default_factory=dict)
    approval: bool = False
    ttl_seconds: float = Field(default=15, gt=0, le=30)

class ResultRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    success: bool
    verified: bool
    result: dict[str, Any] = Field(default_factory=dict)
    verification: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=2000)

def _owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)

def _gateway():
    from aethon.device_gateway_api import gateway
    return gateway

def _transport() -> AndroidCommandTransport:
    return AndroidCommandTransport()

def _enqueue_step(command: dict[str, Any], owner_id: str, transport: AndroidCommandTransport, *, index: int, workflow: dict[str, Any]) -> dict[str, Any] | None:
    steps = workflow.get("steps")
    if not isinstance(steps, list) or not (0 <= index < len(steps)):
        return None
    step = steps[index]
    if not isinstance(step, dict):
        return None
    capability = step.get("capability")
    arguments = step.get("arguments", {})
    if capability not in _ALLOWED or not isinstance(arguments, dict):
        return None
    pending = transport.workflow_step_pending(workflow_id=str(workflow.get("id", "")), owner_id=owner_id, step_index=index)
    if pending:
        return {"command_id": pending["command_id"], "step_index": index, "step_count": len(steps), "capability": pending["capability"], "status": pending["status"]}
    next_workflow = {**workflow, "next_index": index + 1}
    next_command = transport.enqueue(owner_id=owner_id, device_id=command["device_id"], capability=capability, arguments={**arguments, "_workflow": next_workflow}, nonce=secrets.token_urlsafe(24), approved=True, ttl_seconds=15)
    return {"command_id": next_command.command_id, "step_index": index, "step_count": len(steps), "capability": capability, "status": next_command.status}

def _enqueue_next_workflow_step(command: dict[str, Any], owner_id: str, transport: AndroidCommandTransport) -> dict[str, Any] | None:
    workflow = command.get("arguments", {}).get("_workflow")
    if not isinstance(workflow, dict) or workflow.get("state", "RUNNING") != "RUNNING":
        return None
    index = workflow.get("next_index")
    if not isinstance(index, int):
        return None
    return _enqueue_step(command, owner_id, transport, index=index, workflow=workflow)

def _retry_workflow_step(command: dict[str, Any], owner_id: str, transport: AndroidCommandTransport, *, step_index: int, attempt: int) -> dict[str, Any] | None:
    workflow = command.get("arguments", {}).get("_workflow")
    if not isinstance(workflow, dict) or workflow.get("state", "RUNNING") != "RUNNING":
        return None
    retry_workflow = with_attempt(workflow, step_index=step_index, attempt=attempt)
    return _enqueue_step(command, owner_id, transport, index=step_index, workflow=retry_workflow)

@router.post("")
def enqueue(request: EnqueueRequest, owner_id: str = Depends(_owner)):
    if request.capability not in _ALLOWED:
        raise HTTPException(400, "unsupported Android capability")
    if request.capability not in _READ_ONLY and not request.approval:
        raise HTTPException(403, "explicit execution approval required")
    try: device = _gateway().status(device_id=request.device_id, owner_id=owner_id)
    except GatewayError as exc: raise HTTPException(404, str(exc)) from exc
    if request.capability not in set(device["capabilities"]): raise HTTPException(403, "device capability not granted")
    try:
        command = _transport().enqueue(owner_id=owner_id, device_id=request.device_id, capability=request.capability, arguments=request.arguments, nonce=secrets.token_urlsafe(24), approved=request.approval, ttl_seconds=request.ttl_seconds)
    except CommandTransportError as exc: raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "command_id": command.command_id, "device_id": command.device_id, "capability": command.capability, "status": command.status, "expires_at": command.expires_at}

@router.get("/{device_id}/next")
def next_command(device_id: str, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401, "device authentication required")
    token = authorization.split(" ", 1)[1].strip()
    try: device = _gateway().authenticate_any_owner(device_id=device_id, token=token)
    except GatewayError as exc: raise HTTPException(401, str(exc)) from exc
    command = _transport().claim_next(device_id=device_id, owner_id=device.owner_id)
    if command is None: return {"ok": True, "command": None}
    return {"ok": True, "command": {"command_id": command.command_id, "device_id": command.device_id, "capability": command.capability, "arguments": command.arguments, "issued_at": command.issued_at, "expires_at": command.expires_at, "nonce": command.nonce}}

@router.post("/{device_id}/result")
def result(device_id: str, request: ResultRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401, "device authentication required")
    token = authorization.split(" ", 1)[1].strip()
    try: device = _gateway().authenticate_any_owner(device_id=device_id, token=token)
    except GatewayError as exc: raise HTTPException(401, str(exc)) from exc
    transport = _transport()
    command = transport.get(command_id=request.command_id, owner_id=device.owner_id)
    if command is None or command["device_id"] != device_id: raise HTTPException(404, "command not found")
    workflow = command.get("arguments", {}).get("_workflow")
    semantic_verified = True
    step_index = -1
    if isinstance(workflow, dict):
        next_index = workflow.get("next_index")
        steps = workflow.get("steps", [])
        step_index = int(next_index) - 1 if isinstance(next_index, int) else -1
        expected = steps[step_index].get("verify") if 0 <= step_index < len(steps) and isinstance(steps[step_index], dict) else None
        if expected:
            semantic_verified = AndroidWorkflowPlanner.verify({"verify": expected}, request.result)
    effective_verified = request.verified and semantic_verified
    try:
        recorded = transport.record_result(command_id=request.command_id, device_id=device_id, owner_id=device.owner_id, success=request.success, verified=effective_verified, result=request.result, verification=request.verification, error=request.error or ("semantic verification failed" if not semantic_verified else None))
    except CommandTransportError as exc: raise HTTPException(409, str(exc)) from exc

    durable = transport.workflow(workflow_id=str(workflow.get("id")), owner_id=device.owner_id) if isinstance(workflow, dict) and workflow.get("id") else None
    durable_workflow = durable.get("workflow") if isinstance(durable, dict) else None
    workflow_state = durable_workflow.get("state", "RUNNING") if isinstance(durable_workflow, dict) else None
    if recorded["status"] == "COMPLETED":
        if not isinstance(workflow, dict) or workflow_state != "RUNNING":
            return {"ok": True, "result": recorded, "workflow": {"status": workflow_state or "COMPLETED", "next": None}}
        try: next_step = _enqueue_next_workflow_step({**command, "arguments": {**command.get("arguments", {}), "_workflow": durable_workflow}}, device.owner_id, transport)
        except CommandTransportError as exc: raise HTTPException(409, "workflow could not advance") from exc
        return {"ok": True, "result": recorded, "workflow": {"status": "RUNNING" if next_step else "COMPLETED", "next": next_step}}
    if isinstance(workflow, dict) and workflow_state == "RUNNING" and step_index >= 0:
        active_workflow = durable_workflow or workflow
        decision = decide_retry(active_workflow, step_index=step_index, success=request.success, verified=effective_verified)
        if decision.retry:
            try: retry = _retry_workflow_step({**command, "arguments": {**command.get("arguments", {}), "_workflow": active_workflow}}, device.owner_id, transport, step_index=step_index, attempt=decision.attempt)
            except CommandTransportError as exc: raise HTTPException(409, "workflow retry could not be queued") from exc
            return {"ok": True, "result": recorded, "workflow": {"status": "RETRYING", "attempt": decision.attempt, "max_retries": 2, "reason": decision.reason, "next": retry}}
    return {"ok": True, "result": recorded, "workflow": {"status": workflow_state or "FAILED", "next": None}}

@router.get("/status/{command_id}")
def command_status(command_id: str, owner_id: str = Depends(_owner)):
    command = _transport().get(command_id=command_id, owner_id=owner_id)
    if command is None: raise HTTPException(404, "command not found")
    return command

@router.post("/{command_id}/cancel")
def cancel(command_id: str, owner_id: str = Depends(_owner)):
    if not _transport().cancel(command_id=command_id, owner_id=owner_id): raise HTTPException(409, "command cannot be cancelled")
    return {"ok": True, "command_id": command_id, "status": "CANCELLED"}

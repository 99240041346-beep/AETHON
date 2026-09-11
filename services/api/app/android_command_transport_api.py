from __future__ import annotations

import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from aethon.android_command_transport import AndroidCommandTransport, CommandTransportError
from aethon.auth import current_owner, security
from aethon.device_gateway import GatewayError
from app.android_workflow import AndroidWorkflowPlanner

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

def _enqueue_next_workflow_step(command: dict[str, Any], owner_id: str, transport: AndroidCommandTransport) -> dict[str, Any] | None:
    workflow = command.get("arguments", {}).get("_workflow")
    if not isinstance(workflow, dict):
        return None
    steps = workflow.get("steps")
    index = workflow.get("next_index")
    if not isinstance(steps, list) or not isinstance(index, int) or index >= len(steps):
        return None
    step = steps[index]
    capability = step.get("capability")
    arguments = step.get("arguments", {})
    if capability not in _ALLOWED or not isinstance(arguments, dict):
        return None
    next_workflow = {**workflow, "next_index": index + 1}
    next_command = transport.enqueue(owner_id=owner_id, device_id=command["device_id"], capability=capability, arguments={**arguments, "_workflow": next_workflow}, nonce=secrets.token_urlsafe(24), approved=True, ttl_seconds=15)
    return {"command_id": next_command.command_id, "step_index": index, "step_count": len(steps), "capability": capability, "status": next_command.status}

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
    try:
        recorded = transport.record_result(command_id=request.command_id, device_id=device_id, owner_id=device.owner_id, success=request.success, verified=request.verified, result=request.result, verification=request.verification, error=request.error)
    except CommandTransportError as exc: raise HTTPException(409, str(exc)) from exc
    workflow = command.get("arguments", {}).get("_workflow")
    if recorded["status"] != "COMPLETED" or not isinstance(workflow, dict):
        return {"ok": True, "result": recorded, "workflow": {"status": "COMPLETED" if recorded["status"] == "COMPLETED" else "VERIFICATION_FAILED", "next": None}}
    index = int(workflow.get("next_index", 999)) - 1
    steps = workflow.get("steps", [])
    expected = steps[index].get("verify") if 0 <= index < len(steps) and isinstance(steps[index], dict) else None
    if expected and not AndroidWorkflowPlanner.verify({"verify": expected}, request.result):
        return {"ok": True, "result": recorded, "workflow": {"status": "VERIFICATION_FAILED", "next": None}}
    try: next_step = _enqueue_next_workflow_step(command, device.owner_id, transport)
    except CommandTransportError as exc: raise HTTPException(409, "workflow could not advance") from exc
    return {"ok": True, "result": recorded, "workflow": {"status": "RUNNING" if next_step else "COMPLETED", "next": next_step}}

@router.get("/status/{command_id}")
def command_status(command_id: str, owner_id: str = Depends(_owner)):
    command = _transport().get(command_id=command_id, owner_id=owner_id)
    if command is None: raise HTTPException(404, "command not found")
    return command

@router.post("/{command_id}/cancel")
def cancel(command_id: str, owner_id: str = Depends(_owner)):
    if not _transport().cancel(command_id=command_id, owner_id=owner_id): raise HTTPException(409, "command cannot be cancelled")
    return {"ok": True, "command_id": command_id, "status": "CANCELLED"}

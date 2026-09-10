from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aethon.auth import current_owner, security
from aethon.device_gateway import Capability, CommandEnvelope, DeviceGateway, GatewayError

router = APIRouter(prefix="/v1/devices", tags=["devices"])
gateway = DeviceGateway()

class RegisterRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(min_length=1, max_length=40)
    capabilities: set[str] = Field(default_factory=set, max_length=32)

class CommandRequest(BaseModel):
    command_id: str = Field(min_length=1, max_length=128)
    capability: str
    payload: dict[str, Any] = Field(default_factory=dict)
    issued_at: float = Field(default_factory=time.time)
    expires_at: float
    nonce: str = Field(min_length=8, max_length=128)
    idempotency_key: str = Field(min_length=1, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)
    step_id: str | None = Field(default=None, max_length=128)
    approved: bool = False

class HeartbeatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=128)
    device_token: str = Field(min_length=20, max_length=256)

def owner(credentials=Depends(security)) -> str:
    return current_owner(credentials)

def _device_token(token: str | None) -> str:
    if not token or len(token) < 20:
        raise HTTPException(401, "device authentication required")
    return token

@router.post("/register")
def register(request: RegisterRequest, owner_id: str = Depends(owner)):
    try: return gateway.register(owner_id=owner_id, device_id=request.device_id, platform=request.platform, capabilities=request.capabilities)
    except GatewayError as exc: raise HTTPException(400, str(exc)) from exc

@router.post("/heartbeat")
def heartbeat(request: HeartbeatRequest, owner_id: str = Depends(owner)):
    try: return gateway.heartbeat(device_id=request.device_id, token=_device_token(request.device_token), owner_id=owner_id)
    except GatewayError as exc: raise HTTPException(401, str(exc)) from exc

@router.get("/{device_id}")
def device_status(device_id: str, owner_id: str = Depends(owner)):
    try: return gateway.status(device_id=device_id, owner_id=owner_id)
    except GatewayError as exc: raise HTTPException(404, str(exc)) from exc

@router.post("/{device_id}/command")
def command(device_id: str, request: CommandRequest, device_token: str, owner_id: str = Depends(owner)):
    try:
        envelope = CommandEnvelope(command_id=request.command_id, device_id=device_id, capability=request.capability,
            payload=request.payload, issued_at=request.issued_at, expires_at=request.expires_at, nonce=request.nonce,
            idempotency_key=request.idempotency_key, correlation_id=request.correlation_id, task_id=request.task_id,
            step_id=request.step_id, approved=request.approved)
        return gateway.authorize_command(envelope, owner_id=owner_id, token=_device_token(device_token))
    except GatewayError as exc: raise HTTPException(403, str(exc)) from exc

@router.get("")
def capabilities():
    return {"capabilities": [cap.value for cap in Capability], "execution": "bounded-simulator-only"}

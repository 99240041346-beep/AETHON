from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from aethon.android_command_transport import AndroidCommandTransport, CommandTransportError
from aethon.auth import current_owner, security
from aethon.device_gateway import Capability, GatewayError, gateway as _unused

router = APIRouter(prefix="/v1/android/commands", tags=["android-command-transport"])

_ALLOWED = {
    "SCREEN_READ", "APP_LIST", "DEVICE_INFO", "NETWORK_STATUS", "BATTERY_READ", "VOLUME_READ",
    "OPEN_APP", "CLOSE_APP", "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_STOP", "VOLUME_SET",
    "FLASHLIGHT_ON", "FLASHLIGHT_OFF", "SCREEN_CAPTURE",
}
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


def _transport() -> AndroidCommandTransport:
    return AndroidCommandTransport()


def _device_owner(device_id: str, token: str):
    from aethon.device_gateway_api import gateway
    try:
        return gateway.authenticate(device_id=device_id, token=token, owner_id=_owner_for_device(device_id, token)).owner_id
    except GatewayError as exc:
        raise HTTPException(401, str(exc)) from exc


def _owner_for_device(device_id: str, token: str) -> str:
    # Device authentication is deliberately separate from the user bearer token.
    # The gateway's authenticated device record remains the source of owner scope.
    from aethon.device_gateway_api import gateway
    for candidate in ("local-dev",):
        try:
            return gateway.authenticate(device_id=device_id, token=token, owner_id=candidate).owner_id
        except GatewayError:
            continue
    raise HTTPException(401, "device authentication failed")


@router.post("")
def enqueue(request: EnqueueRequest, owner_id: str = Depends(lambda credentials=Depends(security): current_owner(credentials))):
    if request.capability not in _ALLOWED:
        raise HTTPException(400, "unsupported Android capability")
    if request.capability not in _READ_ONLY and not request.approval:
        raise HTTPException(403, "explicit execution approval required")
    from aethon.device_gateway_api import gateway
    try:
        device = gateway.status(device_id=request.device_id, owner_id=owner_id)
    except GatewayError as exc:
        raise HTTPException(404, str(exc)) from exc
    if request.capability not in set(device["capabilities"]) and request.capability != "OPEN_APP":
        raise HTTPException(403, "device capability not granted")
    try:
        command = _transport().enqueue(
            owner_id=owner_id, device_id=request.device_id, capability=request.capability,
            arguments=request.arguments, nonce=__import__('secrets').token_urlsafe(24),
            approved=request.approval, ttl_seconds=request.ttl_seconds,
        )
    except CommandTransportError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "command_id": command.command_id, "device_id": command.device_id,
            "capability": command.capability, "status": command.status, "expires_at": command.expires_at}


@router.get("/{device_id}/next")
def next_command(device_id: str, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "device authentication required")
    token = authorization.split(" ", 1)[1].strip()
    from aethon.device_gateway_api import gateway
    try:
        device = gateway.authenticate_any_owner(device_id=device_id, token=token)
    except GatewayError as exc:
        raise HTTPException(401, str(exc)) from exc
    command = _transport().claim_next(device_id=device_id, owner_id=device.owner_id)
    if command is None:
        return {"ok": True, "command": None}
    return {"ok": True, "command": {"command_id": command.command_id, "device_id": command.device_id,
        "capability": command.capability, "arguments": command.arguments, "issued_at": command.issued_at,
        "expires_at": command.expires_at, "nonce": command.nonce}}


@router.post("/{device_id}/result")
def result(device_id: str, request: ResultRequest, authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "device authentication required")
    token = authorization.split(" ", 1)[1].strip()
    from aethon.device_gateway_api import gateway
    try:
        device = gateway.authenticate_any_owner(device_id=device_id, token=token)
    except GatewayError as exc:
        raise HTTPException(401, str(exc)) from exc
    try:
        return _transport().record_result(command_id=request.command_id, device_id=device_id, owner_id=device.owner_id,
            success=request.success, verified=request.verified, result=request.result,
            verification=request.verification, error=request.error)
    except CommandTransportError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/status/{command_id}")
def command_status(command_id: str, owner_id: str = Depends(lambda credentials=Depends(security): current_owner(credentials))):
    command = _transport().get(command_id=command_id, owner_id=owner_id)
    if command is None:
        raise HTTPException(404, "command not found")
    return command


@router.post("/{command_id}/cancel")
def cancel(command_id: str, owner_id: str = Depends(lambda credentials=Depends(security): current_owner(credentials))):
    if not _transport().cancel(command_id=command_id, owner_id=owner_id):
        raise HTTPException(409, "command cannot be cancelled")
    return {"ok": True, "command_id": command_id, "status": "CANCELLED"}

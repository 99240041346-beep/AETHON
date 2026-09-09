from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.schemas import RiskClass
from aethon.security import SafetyKernel


class GatewayError(ValueError):
    pass


class Capability(str, Enum):
    SCREEN_READ = "SCREEN_READ"
    SCREEN_INTERACT = "SCREEN_INTERACT"
    CAMERA_READ = "CAMERA_READ"
    MICROPHONE_READ = "MICROPHONE_READ"
    LOCATION_READ = "LOCATION_READ"
    NOTIFICATION_READ = "NOTIFICATION_READ"
    APP_OPEN = "APP_OPEN"
    FILE_READ = "FILE_READ"


@dataclass(frozen=True)
class Device:
    device_id: str
    owner_id: str
    platform: str
    capabilities: frozenset[str]
    token_hash: str
    last_seen: float
    nonce: str


@dataclass(frozen=True)
class CommandEnvelope:
    command_id: str
    device_id: str
    capability: str
    payload: dict[str, Any]
    issued_at: float
    expires_at: float
    nonce: str
    idempotency_key: str
    correlation_id: str | None = None
    task_id: str | None = None
    step_id: str | None = None
    approved: bool = False


class DeviceGateway:
    """Bounded device policy boundary; it authenticates and authorizes but never drives hardware."""

    MAX_DEVICES = 1000
    MAX_PAYLOAD_BYTES = 8192
    MAX_TTL_SECONDS = 120
    HEARTBEAT_TTL_SECONDS = 120

    def __init__(self, safety: SafetyExecutionGate | None = None) -> None:
        self.safety = safety or SafetyExecutionGate(SafetyKernel())
        self._devices: dict[str, Device] = {}
        self._used_commands: set[str] = set()
        self._used_nonces: set[str] = set()
        self.audit: list[dict[str, Any]] = []

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def register(self, *, owner_id: str, device_id: str, platform: str, capabilities: set[str]) -> dict[str, str]:
        if not owner_id or not device_id or not platform:
            raise GatewayError("owner, device and platform are required")
        if len(device_id) > 128 or len(platform) > 40:
            raise GatewayError("device identity is too long")
        if len(capabilities) > 32 or any(cap not in {x.value for x in Capability} for cap in capabilities):
            raise GatewayError("undeclared device capability")
        if len(self._devices) >= self.MAX_DEVICES and device_id not in self._devices:
            raise GatewayError("device capacity reached")
        token = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(16)
        self._devices[device_id] = Device(device_id, owner_id, platform, frozenset(capabilities), self._hash(token), time.time(), nonce)
        self._audit("device.registered", device_id, owner_id, {"platform": platform, "capabilities": sorted(capabilities)})
        return {"device_id": device_id, "device_token": token}

    def authenticate(self, *, device_id: str, token: str, owner_id: str) -> Device:
        device = self._devices.get(device_id)
        if not device or device.owner_id != owner_id or not hmac.compare_digest(device.token_hash, self._hash(token)):
            self._audit("device.auth.failed", device_id, owner_id, {})
            raise GatewayError("device authentication failed")
        return device

    def heartbeat(self, *, device_id: str, token: str, owner_id: str) -> dict[str, Any]:
        device = self.authenticate(device_id=device_id, token=token, owner_id=owner_id)
        self._devices[device_id] = Device(device.device_id, device.owner_id, device.platform, device.capabilities, device.token_hash, time.time(), device.nonce)
        self._audit("device.heartbeat", device_id, owner_id, {})
        return {"ok": True, "device_id": device_id, "last_seen": self._devices[device_id].last_seen}

    def authorize_command(self, envelope: CommandEnvelope, *, owner_id: str, token: str) -> dict[str, Any]:
        device = self.authenticate(device_id=envelope.device_id, token=token, owner_id=owner_id)
        now = time.time()
        if envelope.command_id in self._used_commands or envelope.nonce in self._used_nonces:
            raise GatewayError("replayed command envelope")
        if envelope.expires_at <= now or envelope.issued_at > now + 10:
            raise GatewayError("expired or future-dated command envelope")
        if envelope.expires_at - envelope.issued_at > self.MAX_TTL_SECONDS:
            raise GatewayError("command TTL exceeds limit")
        if envelope.capability not in device.capabilities:
            raise GatewayError("device capability not granted")
        if len(str(envelope.payload).encode("utf-8")) > self.MAX_PAYLOAD_BYTES:
            raise GatewayError("command payload too large")
        risk = RiskClass.LOW if envelope.capability.endswith("_READ") or envelope.capability == Capability.APP_OPEN.value else RiskClass.MEDIUM
        try:
            decision = self.safety.authorize(risk, side_effects=risk != RiskClass.LOW, approved=envelope.approved)
        except ExecutionAuthorizationError as exc:
            self._audit("device.command.blocked", envelope.device_id, owner_id, {"command_id": envelope.command_id, "reason": str(exc)})
            raise GatewayError(str(exc)) from exc
        self._used_commands.add(envelope.command_id)
        self._used_nonces.add(envelope.nonce)
        self._audit("device.command.authorized", envelope.device_id, owner_id, {"command_id": envelope.command_id, "capability": envelope.capability, "effective_decision": decision.effective_decision})
        return {"ok": True, "authorized": True, "command_id": envelope.command_id, "device_id": envelope.device_id, "capability": envelope.capability, "dispatch": "simulator", "verified": False}

    def status(self, *, device_id: str, owner_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device or device.owner_id != owner_id:
            raise GatewayError("device not found")
        return {"device_id": device.device_id, "platform": device.platform, "capabilities": sorted(device.capabilities), "last_seen": device.last_seen, "online": time.time() - device.last_seen <= self.HEARTBEAT_TTL_SECONDS}

    def _audit(self, event: str, device_id: str, owner_id: str, data: dict[str, Any]) -> None:
        self.audit.append({"event": event, "device_id": device_id, "owner_id": owner_id, "timestamp": time.time(), "data": data})

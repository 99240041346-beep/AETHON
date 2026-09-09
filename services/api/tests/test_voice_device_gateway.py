import time

import pytest

from aethon.device_gateway import CommandEnvelope, DeviceGateway, GatewayError
from aethon.execution_safety_gate import SafetyExecutionGate
from aethon.schemas import RiskClass
from aethon.security import SafetyKernel
from aethon.voice_api import VoiceRequest, respond


def test_voice_request_limits_and_telugu_fallback(monkeypatch):
    monkeypatch.setattr("aethon.voice_api.model_router", type("R", (), {"generate": lambda self, prompt: (_ for _ in ()).throw(RuntimeError("offline")), "provider": type("P", (), {"name": "test"})()})())
    result = respond(VoiceRequest(transcript="నా ఫోన్ బ్యాటరీ ఎంత?", language="te-IN"), owner_id="owner-1")
    assert result.ok is True
    assert result.provider == "deterministic-fallback"
    assert "నా ఫోన్" in result.response


def test_device_register_auth_heartbeat_and_capability():
    gateway = DeviceGateway()
    registration = gateway.register(owner_id="owner-1", device_id="phone-1", platform="android", capabilities={"SCREEN_READ"})
    assert gateway.status(device_id="phone-1", owner_id="owner-1")["online"] is True
    heartbeat = gateway.heartbeat(device_id="phone-1", token=registration["device_token"], owner_id="owner-1")
    assert heartbeat["ok"] is True
    now = time.time()
    command = CommandEnvelope("cmd-1", "phone-1", "SCREEN_READ", {}, now, now + 30, "nonce-1234", "idem-1")
    result = gateway.authorize_command(command, owner_id="owner-1", token=registration["device_token"])
    assert result["authorized"] is True
    assert result["dispatch"] == "simulator"


def test_device_gateway_rejects_replay_and_undeclared_capability():
    gateway = DeviceGateway()
    registration = gateway.register(owner_id="owner-1", device_id="phone-1", platform="android", capabilities={"SCREEN_READ"})
    now = time.time()
    command = CommandEnvelope("cmd-1", "phone-1", "SCREEN_READ", {}, now, now + 30, "nonce-1234", "idem-1")
    gateway.authorize_command(command, owner_id="owner-1", token=registration["device_token"])
    with pytest.raises(GatewayError, match="replayed"):
        gateway.authorize_command(command, owner_id="owner-1", token=registration["device_token"])
    denied = CommandEnvelope("cmd-2", "phone-1", "SCREEN_INTERACT", {}, now, now + 30, "nonce-5678", "idem-2")
    with pytest.raises(GatewayError, match="capability"):
        gateway.authorize_command(denied, owner_id="owner-1", token=registration["device_token"])


def test_device_gateway_requires_approval_for_side_effect_capability():
    gateway = DeviceGateway(SafetyExecutionGate(SafetyKernel()))
    registration = gateway.register(owner_id="owner-1", device_id="phone-1", platform="android", capabilities={"SCREEN_INTERACT"})
    now = time.time()
    command = CommandEnvelope("cmd-1", "phone-1", "SCREEN_INTERACT", {}, now, now + 30, "nonce-1234", "idem-1")
    with pytest.raises(GatewayError, match="approval"):
        gateway.authorize_command(command, owner_id="owner-1", token=registration["device_token"])
    approved = CommandEnvelope("cmd-2", "phone-1", "SCREEN_INTERACT", {}, now, now + 30, "nonce-5678", "idem-2", approved=True)
    result = gateway.authorize_command(approved, owner_id="owner-1", token=registration["device_token"])
    assert result["authorized"] is True


def test_device_gateway_rejects_expired_command():
    gateway = DeviceGateway()
    registration = gateway.register(owner_id="owner-1", device_id="phone-1", platform="android", capabilities={"SCREEN_READ"})
    now = time.time()
    command = CommandEnvelope("cmd-1", "phone-1", "SCREEN_READ", {}, now - 100, now - 1, "nonce-1234", "idem-1")
    with pytest.raises(GatewayError, match="expired"):
        gateway.authorize_command(command, owner_id="owner-1", token=registration["device_token"])

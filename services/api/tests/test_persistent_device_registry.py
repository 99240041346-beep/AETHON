from __future__ import annotations

import time

import pytest

from aethon.device_gateway import CommandEnvelope, DeviceGateway, GatewayError
from aethon.device_registry_store import StoredDevice


class FakeRegistry:
    def __init__(self) -> None:
        self.devices: dict[str, StoredDevice] = {}
        self.nonces: set[str] = set()

    def get(self, *, device_id: str):
        return self.devices.get(device_id)

    def create(self, *, device_id, owner_id, platform, capabilities, token_hash, registration_nonce):
        if device_id in self.devices:
            raise RuntimeError("duplicate")
        self.devices[device_id] = StoredDevice(device_id, owner_id, platform, frozenset(capabilities), token_hash, time.time(), registration_nonce)

    def heartbeat(self, *, device_id, owner_id):
        current = self.devices[device_id]
        updated = StoredDevice(current.device_id, current.owner_id, current.platform, current.capabilities, current.token_hash, time.time(), current.registration_nonce)
        self.devices[device_id] = updated
        return updated

    def mark_replay_nonce(self, *, nonce, device_id, command_id):
        if nonce in self.nonces:
            return False
        self.nonces.add(nonce)
        return True

    def status(self, *, device_id, owner_id, heartbeat_ttl):
        current = self.devices.get(device_id)
        if not current or current.owner_id != owner_id:
            raise RuntimeError("device not found")
        return {"device_id": current.device_id, "platform": current.platform, "capabilities": sorted(current.capabilities), "last_seen": current.last_seen, "online": True}


def test_gateway_survives_new_instance_with_same_registry() -> None:
    registry = FakeRegistry()
    first = DeviceGateway(registry=registry)
    registration = first.register(owner_id="owner-1", device_id="android-1", platform="android", capabilities={"DEVICE_INFO"})

    second = DeviceGateway(registry=registry)
    authenticated = second.authenticate(device_id="android-1", token=registration["device_token"], owner_id="owner-1")

    assert authenticated.device_id == "android-1"
    assert second.status(device_id="android-1", owner_id="owner-1")["online"] is True


def test_persistent_nonce_replay_is_cross_instance() -> None:
    registry = FakeRegistry()
    first = DeviceGateway(registry=registry)
    registration = first.register(owner_id="owner-1", device_id="android-1", platform="android", capabilities={"DEVICE_INFO"})
    now = time.time()
    envelope = CommandEnvelope("cmd-1", "android-1", "DEVICE_INFO", {}, now, now + 10, "nonce-1", "idem-1")

    assert first.authorize_command(envelope, owner_id="owner-1", token=registration["device_token"])["authorized"] is True

    second = DeviceGateway(registry=registry)
    with pytest.raises(GatewayError, match="replayed command envelope"):
        second.authorize_command(envelope, owner_id="owner-1", token=registration["device_token"])


def test_wrong_owner_cannot_read_persistent_device() -> None:
    registry = FakeRegistry()
    gateway = DeviceGateway(registry=registry)
    registration = gateway.register(owner_id="owner-1", device_id="android-1", platform="android", capabilities={"DEVICE_INFO"})

    with pytest.raises(GatewayError, match="device authentication failed"):
        gateway.authenticate(device_id="android-1", token=registration["device_token"], owner_id="owner-2")

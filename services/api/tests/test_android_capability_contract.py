import time

import pytest

from aethon.device_gateway import Capability, CommandEnvelope, DeviceGateway, GatewayError


ANDROID_CAPABILITIES = {
    "SCREEN_READ", "APP_LIST", "DEVICE_INFO", "NETWORK_STATUS", "BATTERY_READ", "VOLUME_READ",
    "OPEN_APP", "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_STOP", "VOLUME_SET",
    "FLASHLIGHT_ON", "FLASHLIGHT_OFF", "SCREEN_CAPTURE",
}


def test_gateway_accepts_native_android_capabilities() -> None:
    gateway = DeviceGateway()
    result = gateway.register(
        owner_id="owner-1",
        device_id="android-1",
        platform="android",
        capabilities=ANDROID_CAPABILITIES,
    )
    assert result["device_id"] == "android-1"
    assert len(result["device_token"]) >= 20
    status = gateway.status(device_id="android-1", owner_id="owner-1")
    assert ANDROID_CAPABILITIES.issubset(set(status["capabilities"]))


def test_legacy_app_open_remains_accepted_by_gateway() -> None:
    assert Capability.APP_OPEN.value == "APP_OPEN"
    gateway = DeviceGateway()
    result = gateway.register(
        owner_id="owner-1",
        device_id="android-legacy",
        platform="android",
        capabilities={"APP_OPEN"},
    )
    assert result["device_id"] == "android-legacy"


def test_native_open_app_is_authorized_as_low_risk() -> None:
    gateway = DeviceGateway()
    registration = gateway.register(
        owner_id="owner-1",
        device_id="android-1",
        platform="android",
        capabilities={"OPEN_APP"},
    )
    now = time.time()
    envelope = CommandEnvelope(
        command_id="cmd-1",
        device_id="android-1",
        capability="OPEN_APP",
        payload={"package_name": "com.example.app"},
        issued_at=now,
        expires_at=now + 15,
        nonce="nonce-open-app-1",
        idempotency_key="idem-1",
    )
    result = gateway.authorize_command(envelope, owner_id="owner-1", token=registration["device_token"])
    assert result["authorized"] is True
    assert result["capability"] == "OPEN_APP"
    assert result["verified"] is False


def test_unimplemented_close_app_is_not_in_gateway_contract() -> None:
    gateway = DeviceGateway()
    with pytest.raises(GatewayError, match="undeclared device capability"):
        gateway.register(
            owner_id="owner-1",
            device_id="android-1",
            platform="android",
            capabilities={"CLOSE_APP"},
        )

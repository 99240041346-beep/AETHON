def test_device_gateway_contract():
    from aethon.device_gateway import Capability, DeviceGateway
    assert Capability.SCREEN_READ.value == "SCREEN_READ"
    assert "SHELL_EXECUTE" not in {x.value for x in Capability}
    assert DeviceGateway.MAX_TTL_SECONDS == 120

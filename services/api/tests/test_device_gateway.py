from aethon.device_gateway import Capability


def test_capability_enum_is_bounded():
    assert Capability.SCREEN_READ.value == "SCREEN_READ"
    assert "SHELL_EXECUTE" not in {cap.value for cap in Capability}

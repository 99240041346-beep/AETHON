from aethon.software_engineering import BoundedSoftwareEngineeringAgent, SoftwareOperation


def test_compatibility_export():
    assert BoundedSoftwareEngineeringAgent
    assert SoftwareOperation.DIFF.value == "diff"

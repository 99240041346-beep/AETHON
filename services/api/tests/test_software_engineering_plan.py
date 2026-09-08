from app.software_engineering import BoundedSoftwareEngineeringAgent, SoftwareOperation


def test_conservative_plan():
    action = BoundedSoftwareEngineeringAgent().plan("improve tests")[0]
    assert action.operation == SoftwareOperation.DIFF

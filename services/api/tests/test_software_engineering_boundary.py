import pytest
from app.software_engineering import BoundedSoftwareEngineeringAgent, SoftwareSecurityError


def test_traversal_rejected():
    with pytest.raises(SoftwareSecurityError):
        BoundedSoftwareEngineeringAgent().validate_path("../outside")

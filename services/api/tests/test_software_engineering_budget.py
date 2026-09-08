import pytest

from app.software_engineering import BoundedSoftwareEngineeringAgent, SoftwareOperation, SoftwareRequest, SoftwareSecurityError


def test_operation_budget_rejects_oversized_batch():
    agent = BoundedSoftwareEngineeringAgent(max_operations=1)
    with pytest.raises(SoftwareSecurityError):
        agent.validate_requests([
            SoftwareRequest(SoftwareOperation.DIFF),
            SoftwareRequest(SoftwareOperation.DIFF),
        ])

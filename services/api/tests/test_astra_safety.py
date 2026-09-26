from aethon.astra_safety import ASTRASafety
from aethon.schemas import RiskClass


def test_astra_safety_preserves_canonical_decisions():
    safety = ASTRASafety()
    assert safety.decide(RiskClass.LOW) == "ALLOW"
    assert safety.decide(RiskClass.HIGH) == "APPROVAL_REQUIRED"
    assert safety.decide(RiskClass.CRITICAL) == "DENY"
    assert safety.decide(RiskClass.LOW, side_effects=True) == "APPROVAL_REQUIRED"

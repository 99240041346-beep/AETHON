from aethon.schemas import RiskClass

class SafetyKernel:
    def authorize(self, risk: RiskClass, side_effects: bool = False) -> str:
        if risk == RiskClass.CRITICAL:
            return 'DENY'
        if side_effects or risk in {RiskClass.HIGH, RiskClass.MEDIUM}:
            return 'APPROVAL_REQUIRED'
        return 'ALLOW'

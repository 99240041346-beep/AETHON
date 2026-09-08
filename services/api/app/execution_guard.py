from __future__ import annotations

from dataclasses import dataclass

from aethon.schemas import RiskClass
from aethon.security import SafetyKernel


class ExecutionGuardError(PermissionError):
    pass


@dataclass(frozen=True)
class ExecutionDecision:
    decision: str
    risk: RiskClass
    side_effects: bool
    approved: bool


class ExecutionGuard:
    """Single execution authorization boundary for tool adapters.

    This guard does not grant authority. It only converts the authoritative
    SafetyKernel decision into an executable/blocked outcome and requires an
    explicit approval flag for approval-gated operations.
    """

    def __init__(self, safety: SafetyKernel | None = None) -> None:
        self.safety = safety or SafetyKernel()

    def evaluate(self, risk: RiskClass, side_effects: bool = False, *, approved: bool = False) -> ExecutionDecision:
        decision = self.safety.authorize(risk, side_effects)
        if decision == "DENY":
            raise ExecutionGuardError("execution denied by safety policy")
        if decision == "APPROVAL_REQUIRED" and not approved:
            raise ExecutionGuardError("explicit execution approval required")
        return ExecutionDecision(decision, risk, side_effects, approved)


__all__ = ["ExecutionDecision", "ExecutionGuard", "ExecutionGuardError"]

from __future__ import annotations

from dataclasses import dataclass

from aethon.schemas import RiskClass
from aethon.security import SafetyKernel


class ExecutionAuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class AuthorizationDecision:
    policy_decision: str
    effective_decision: str
    risk: RiskClass
    side_effects: bool
    approved: bool


class SafetyExecutionGate:
    """Fail-closed SafetyKernel boundary; does not execute tools."""

    def __init__(self, safety: SafetyKernel | None = None) -> None:
        self.safety = safety or SafetyKernel()

    def authorize(self, risk: RiskClass, side_effects: bool = False, *, approved: bool = False) -> AuthorizationDecision:
        policy = self.safety.authorize(risk, side_effects)
        if policy == "DENY":
            raise ExecutionAuthorizationError("execution denied by safety policy")
        if policy == "APPROVAL_REQUIRED" and not approved:
            raise ExecutionAuthorizationError("explicit execution approval required")
        return AuthorizationDecision(policy, "ALLOW", risk, side_effects, approved)


__all__ = ["AuthorizationDecision", "ExecutionAuthorizationError", "SafetyExecutionGate"]

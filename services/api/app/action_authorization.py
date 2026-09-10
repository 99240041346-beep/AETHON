from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from aethon.assistant_command_bridge import CommandIntent
from aethon.execution_safety_gate import ExecutionAuthorizationError, SafetyExecutionGate
from aethon.schemas import RiskClass


class AuthorizationState(str, Enum):
    CLASSIFIED = "CLASSIFIED"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class AuthorizedAction:
    action: str
    arguments: dict[str, Any]
    state: AuthorizationState


class ActionAuthorizer:
    """Separates intent classification from execution authorization."""

    def __init__(self, safety_gate: SafetyExecutionGate | None = None) -> None:
        self.safety_gate = safety_gate or SafetyExecutionGate()

    def authorize(self, intent: CommandIntent, *, approved: bool = False) -> AuthorizedAction:
        if intent.action == "android.open_app":
            self.safety_gate.authorize(RiskClass.LOW, side_effects=False, approved=approved)
            package = intent.arguments.get("package")
            if not isinstance(package, str) or package not in {
                "com.google.android.youtube",
                "com.android.chrome",
                "com.google.android.calculator",
                "com.android.settings",
            }:
                raise ExecutionAuthorizationError("unallowlisted Android package")
            return AuthorizedAction(intent.action, dict(intent.arguments), AuthorizationState.AUTHORIZED)
        raise ExecutionAuthorizationError("unsupported assistant action")

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    reason: str
    evidence: dict[str, Any]


class Verifier(Protocol):
    def verify(self, goal: str, result: Any) -> VerificationResult: ...


class BasicVerifier:
    """Deterministic AETHON-0 verifier.

    It enforces a conservative invariant: a successful task must have a
    non-empty result and a result that can be represented as text. Future
    verifiers can add goal-specific checks without changing the runtime API.
    """

    def verify(self, goal: str, result: Any) -> VerificationResult:
        if result is None:
            return VerificationResult(False, "result is None", {"goal_nonempty": bool(goal)})
        text = str(result).strip()
        if not text:
            return VerificationResult(False, "result is empty", {"goal_nonempty": bool(goal)})
        return VerificationResult(
            True,
            "basic output verification passed",
            {"goal_nonempty": bool(goal), "result_nonempty": True, "result_type": type(result).__name__},
        )

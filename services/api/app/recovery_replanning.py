from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureClass(str, Enum):
    TRANSIENT = "TRANSIENT"
    TIMEOUT = "TIMEOUT"
    DEPENDENCY = "DEPENDENCY"
    VERIFICATION = "VERIFICATION"
    SAFETY = "SAFETY"
    PERMANENT = "PERMANENT"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"


class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    BLOCK = "BLOCK"
    ABORT = "ABORT"
    CANCEL = "CANCEL"


@dataclass(frozen=True)
class RecoveryPolicy:
    max_attempts: int = 3
    max_replans: int = 2
    base_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    max_recovery_seconds: float = 300.0

    def __post_init__(self) -> None:
        if not 0 <= self.max_attempts <= 10:
            raise ValueError("max_attempts must be between 0 and 10")
        if not 0 <= self.max_replans <= 10:
            raise ValueError("max_replans must be between 0 and 10")
        if self.base_backoff_seconds <= 0:
            raise ValueError("base_backoff_seconds must be > 0")
        if self.max_backoff_seconds < self.base_backoff_seconds:
            raise ValueError("max_backoff_seconds must be >= base_backoff_seconds")
        if self.max_recovery_seconds <= 0:
            raise ValueError("max_recovery_seconds must be > 0")


@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    attempt: int
    replans_used: int
    delay_seconds: float
    reason: str


class RecoveryPlanner:
    """Deterministic, bounded recovery decisions; never grants safety authority."""

    def __init__(self, policy: RecoveryPolicy | None = None) -> None:
        self.policy = policy or RecoveryPolicy()

    def backoff(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        return min(
            self.policy.max_backoff_seconds,
            self.policy.base_backoff_seconds * (2 ** (attempt - 1)),
        )

    def decide(
        self,
        failure: FailureClass,
        *,
        attempt: int,
        replans_used: int = 0,
        elapsed_seconds: float = 0.0,
        safety_allowed: bool = True,
    ) -> RecoveryDecision:
        if attempt < 0:
            raise ValueError("attempt must be >= 0")
        if replans_used < 0:
            raise ValueError("replans_used must be >= 0")
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be >= 0")

        if not safety_allowed or failure is FailureClass.SAFETY:
            return RecoveryDecision(RecoveryAction.BLOCK, attempt, replans_used, 0.0, "safety policy denied recovery")
        if failure is FailureClass.CANCELLED:
            return RecoveryDecision(RecoveryAction.CANCEL, attempt, replans_used, 0.0, "recovery cancelled")
        if elapsed_seconds >= self.policy.max_recovery_seconds:
            return RecoveryDecision(RecoveryAction.ABORT, attempt, replans_used, 0.0, "recovery deadline exceeded")
        if failure is FailureClass.PERMANENT or failure is FailureClass.UNKNOWN:
            return RecoveryDecision(RecoveryAction.ABORT, attempt, replans_used, 0.0, "failure is not safely retryable")

        retryable = failure in {FailureClass.TRANSIENT, FailureClass.TIMEOUT, FailureClass.VERIFICATION}
        if retryable and attempt < self.policy.max_attempts:
            next_attempt = attempt + 1
            delay = self.backoff(next_attempt)
            if elapsed_seconds + delay <= self.policy.max_recovery_seconds:
                return RecoveryDecision(RecoveryAction.RETRY, next_attempt, replans_used, delay, "bounded retry")

        if failure in {FailureClass.DEPENDENCY, FailureClass.VERIFICATION, FailureClass.TRANSIENT, FailureClass.TIMEOUT}:
            if replans_used < self.policy.max_replans:
                return RecoveryDecision(RecoveryAction.REPLAN, attempt, replans_used + 1, 0.0, "bounded local replanning")

        return RecoveryDecision(RecoveryAction.ABORT, attempt, replans_used, 0.0, "recovery budget exhausted")


def bounded_alternatives(
    alternatives: list[str],
    *,
    max_alternatives: int = 5,
    max_length: int = 500,
) -> tuple[str, ...]:
    """Return deterministic, bounded, case-insensitive unique alternatives."""
    if not 1 <= max_alternatives <= 20:
        raise ValueError("max_alternatives must be between 1 and 20")
    if not 1 <= max_length <= 2000:
        raise ValueError("max_length must be between 1 and 2000")
    result: list[str] = []
    seen: set[str] = set()
    for raw in alternatives:
        value = raw.strip()
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value[:max_length])
        if len(result) >= max_alternatives:
            break
    return tuple(result)


@dataclass(frozen=True)
class RecoveryCompletion:
    status: str
    reason: str


def complete_recovery(*, executed: bool, verified: bool, cancelled: bool = False) -> RecoveryCompletion:
    """Recovery is successful only after execution occurred and verification passed."""
    if cancelled:
        return RecoveryCompletion("CANCELLED", "recovery cancelled")
    if not executed:
        return RecoveryCompletion("INCOMPLETE", "recovery action was not executed")
    if not verified:
        return RecoveryCompletion("FAILED_VERIFICATION", "recovery action did not pass verification")
    return RecoveryCompletion("RECOVERED", "recovery action verified")


__all__ = [
    "FailureClass",
    "RecoveryAction",
    "RecoveryCompletion",
    "RecoveryDecision",
    "RecoveryPlanner",
    "RecoveryPolicy",
    "bounded_alternatives",
    "complete_recovery",
]

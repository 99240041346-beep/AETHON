from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_STEP_RETRIES = 2


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    attempt: int
    reason: str


def decide_retry(workflow: dict[str, Any], *, step_index: int, success: bool, verified: bool) -> RetryDecision:
    """Return a bounded retry decision for one workflow step.

    Retries are deliberately conservative: only failed/unverified execution may
    retry, and each step gets at most MAX_STEP_RETRIES retries after its first
    attempt. A successful and verified step is never duplicated.
    """
    if success and verified:
        return RetryDecision(False, 0, "step verified")
    attempts = workflow.get("attempts", {})
    if not isinstance(attempts, dict):
        attempts = {}
    raw = attempts.get(str(step_index), 0)
    try:
        attempt = int(raw)
    except (TypeError, ValueError):
        attempt = 0
    if attempt < 0:
        attempt = 0
    if attempt >= MAX_STEP_RETRIES:
        return RetryDecision(False, attempt, "retry limit reached")
    return RetryDecision(True, attempt + 1, "step failed or verification failed")


def with_attempt(workflow: dict[str, Any], *, step_index: int, attempt: int) -> dict[str, Any]:
    attempts = workflow.get("attempts", {})
    attempts = dict(attempts) if isinstance(attempts, dict) else {}
    attempts[str(step_index)] = attempt
    return {**workflow, "attempts": attempts}

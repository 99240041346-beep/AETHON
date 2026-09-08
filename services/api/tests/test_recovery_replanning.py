from app.recovery_replanning import (
    FailureClass,
    RecoveryAction,
    RecoveryPlanner,
    RecoveryPolicy,
    bounded_alternatives,
    complete_recovery,
)


def test_backoff_is_deterministic_and_bounded() -> None:
    planner = RecoveryPlanner(RecoveryPolicy(base_backoff_seconds=2, max_backoff_seconds=5))
    assert [planner.backoff(i) for i in range(1, 5)] == [2, 4, 5, 5]


def test_transient_failure_retries_with_budget() -> None:
    planner = RecoveryPlanner(RecoveryPolicy(max_attempts=2))
    decision = planner.decide(FailureClass.TRANSIENT, attempt=0)
    assert decision.action is RecoveryAction.RETRY
    assert decision.attempt == 1
    assert decision.delay_seconds == 1


def test_exhausted_retry_budget_replans_then_aborts() -> None:
    planner = RecoveryPlanner(RecoveryPolicy(max_attempts=1, max_replans=1))
    first = planner.decide(FailureClass.VERIFICATION, attempt=1)
    assert first.action is RecoveryAction.REPLAN
    second = planner.decide(FailureClass.VERIFICATION, attempt=1, replans_used=1)
    assert second.action is RecoveryAction.ABORT


def test_safety_denial_cannot_be_bypassed_by_recovery() -> None:
    planner = RecoveryPlanner()
    decision = planner.decide(FailureClass.TRANSIENT, attempt=0, safety_allowed=False)
    assert decision.action is RecoveryAction.BLOCK
    assert decision.delay_seconds == 0


def test_deadline_blocks_further_recovery() -> None:
    planner = RecoveryPlanner(RecoveryPolicy(max_recovery_seconds=3))
    decision = planner.decide(FailureClass.TRANSIENT, attempt=0, elapsed_seconds=3)
    assert decision.action is RecoveryAction.ABORT


def test_unknown_and_permanent_failures_abort() -> None:
    planner = RecoveryPlanner()
    assert planner.decide(FailureClass.UNKNOWN, attempt=0).action is RecoveryAction.ABORT
    assert planner.decide(FailureClass.PERMANENT, attempt=0).action is RecoveryAction.ABORT


def test_alternatives_are_bounded_and_deduplicated() -> None:
    assert bounded_alternatives([" A ", "a", "", "B", "C"], max_alternatives=2) == ("A", "B")


def test_recovery_requires_verification_for_success() -> None:
    assert complete_recovery(executed=False, verified=True).status == "INCOMPLETE"
    assert complete_recovery(executed=True, verified=False).status == "FAILED_VERIFICATION"
    assert complete_recovery(executed=True, verified=True).status == "RECOVERED"
    assert complete_recovery(executed=True, verified=True, cancelled=True).status == "CANCELLED"

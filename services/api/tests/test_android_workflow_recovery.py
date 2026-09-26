from app.android_workflow_recovery import MAX_STEP_RETRIES, decide_retry, with_attempt


def test_success_is_never_retried():
    decision = decide_retry({}, step_index=0, success=True, verified=True)
    assert decision.retry is False


def test_failed_step_gets_two_bounded_retries():
    workflow = {}
    first = decide_retry(workflow, step_index=0, success=False, verified=False)
    assert first.retry and first.attempt == 1
    workflow = with_attempt(workflow, step_index=0, attempt=first.attempt)
    second = decide_retry(workflow, step_index=0, success=False, verified=False)
    assert second.retry and second.attempt == 2
    workflow = with_attempt(workflow, step_index=0, attempt=second.attempt)
    final = decide_retry(workflow, step_index=0, success=False, verified=False)
    assert final.retry is False
    assert final.attempt == MAX_STEP_RETRIES


def test_attempts_are_isolated_per_step():
    workflow = with_attempt({}, step_index=1, attempt=2)
    decision = decide_retry(workflow, step_index=0, success=False, verified=False)
    assert decision.retry and decision.attempt == 1

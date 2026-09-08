import pytest

from aethon.approval_lifecycle import ApprovalLifecycle, ApprovalLifecycleError, ApprovalRequest


def _request(tool="write_file"):
    return ApprovalRequest("task-1", "step-1", tool, "HIGH", True)


def test_request_requires_explicit_approval_before_consume():
    lifecycle = ApprovalLifecycle()
    lifecycle.request(_request())
    assert lifecycle.has_approval("task-1", "step-1", "write_file") is False
    with pytest.raises(ApprovalLifecycleError):
        lifecycle.consume("task-1", "step-1", "write_file")


def test_approval_is_scoped_to_exact_task_step_and_tool():
    lifecycle = ApprovalLifecycle()
    lifecycle.request(_request())
    lifecycle.approve("task-1", "step-1", "operator")
    assert lifecycle.has_approval("task-1", "step-1", "other_tool") is False
    with pytest.raises(ApprovalLifecycleError):
        lifecycle.consume("task-1", "step-1", "other_tool")
    assert lifecycle.has_approval("task-1", "step-1", "write_file") is True
    record = lifecycle.consume("task-1", "step-1", "write_file")
    assert record.approver == "operator"
    assert lifecycle.has_approval("task-1", "step-1", "write_file") is False


def test_unknown_or_missing_approver_fails_closed():
    lifecycle = ApprovalLifecycle()
    lifecycle.request(_request())
    with pytest.raises(ApprovalLifecycleError):
        lifecycle.approve("task-1", "step-1", "")
    with pytest.raises(ApprovalLifecycleError):
        lifecycle.approve("task-2", "step-1", "operator")


def test_duplicate_approval_replaces_only_same_pending_request():
    lifecycle = ApprovalLifecycle()
    lifecycle.request(_request())
    lifecycle.approve("task-1", "step-1", "operator")
    with pytest.raises(ApprovalLifecycleError):
        lifecycle.approve("task-1", "step-1", "operator-2")


def test_clear_revokes_pending_or_approved_state():
    lifecycle = ApprovalLifecycle()
    lifecycle.request(_request())
    lifecycle.clear("task-1", "step-1")
    assert lifecycle.pending("task-1", "step-1") is None
    with pytest.raises(ApprovalLifecycleError):
        lifecycle.consume("task-1", "step-1", "write_file")

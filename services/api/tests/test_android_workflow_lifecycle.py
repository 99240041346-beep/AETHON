from types import SimpleNamespace

from app.android_command_transport_api import _enqueue_next_workflow_step, _enqueue_step, _retry_workflow_step


class FakeTransport:
    def __init__(self, pending=None):
        self.pending = pending
        self.enqueued = []

    def workflow_step_pending(self, *, workflow_id, owner_id, step_index):
        return self.pending

    def enqueue(self, **kwargs):
        self.enqueued.append(kwargs)
        return SimpleNamespace(command_id="new-command", status="ACCEPTED")

    def enqueue_workflow_step(self, **kwargs):
        if self.pending:
            return SimpleNamespace(command_id=self.pending["command_id"], capability=self.pending["capability"], status=self.pending["status"])
        return self.enqueue(**kwargs)


def _command(workflow):
    return {"device_id": "device-1", "arguments": {"_workflow": workflow}}


def test_paused_workflow_cannot_auto_advance():
    transport = FakeTransport()
    workflow = {"id": "wf-1", "state": "PAUSED", "next_index": 1, "steps": [{"capability": "SCREEN_READ", "arguments": {}}]}
    assert _enqueue_next_workflow_step(_command(workflow), "owner-1", transport) is None
    assert transport.enqueued == []


def test_cancelled_workflow_cannot_auto_advance_or_retry():
    transport = FakeTransport()
    workflow = {"id": "wf-1", "state": "CANCELLED", "next_index": 1, "steps": [{"capability": "SCREEN_READ", "arguments": {}}]}
    command = _command(workflow)
    assert _enqueue_next_workflow_step(command, "owner-1", transport) is None
    assert _retry_workflow_step(command, "owner-1", transport, step_index=0, attempt=1) is None
    assert transport.enqueued == []


def test_resume_path_does_not_duplicate_an_existing_step():
    transport = FakeTransport(pending={"command_id": "existing", "capability": "SCREEN_READ", "status": "ACCEPTED"})
    workflow = {"id": "wf-1", "state": "RUNNING", "next_index": 1, "steps": [{"capability": "SCREEN_READ", "arguments": {}}]}
    result = _enqueue_step(_command(workflow), "owner-1", transport, index=0, workflow=workflow)
    assert result["command_id"] == "existing"
    assert transport.enqueued == []


def test_retry_attempt_is_persisted_in_workflow_metadata():
    transport = FakeTransport()
    workflow = {"id": "wf-1", "state": "RUNNING", "next_index": 1, "steps": [{"capability": "SCREEN_READ", "arguments": {}}], "attempts": {"0": 1}}
    result = _retry_workflow_step(_command(workflow), "owner-1", transport, step_index=0, attempt=2)
    assert result["command_id"] == "new-command"
    assert transport.enqueued[0]["arguments"]["_workflow"]["attempts"]["0"] == 2

from app.android_command_transport_api import _enqueue_step


class FakeCommand:
    command_id = "cmd-idempotent"
    capability = "SCREEN_CLICK"
    status = "ACCEPTED"


class FakeTransport:
    def __init__(self):
        self.calls = []

    def enqueue_workflow_step(self, **kwargs):
        self.calls.append(kwargs)
        return FakeCommand()


def test_workflow_step_enqueue_uses_idempotent_transport():
    transport = FakeTransport()
    workflow = {"id": "wf-1", "steps": [{"capability": "SCREEN_CLICK", "arguments": {"text": "Search"}}], "state": "RUNNING", "next_index": 0}

    result = _enqueue_step({"device_id": "device-1"}, "owner-1", transport, index=0, workflow=workflow)

    assert result == {
        "command_id": "cmd-idempotent",
        "step_index": 0,
        "step_count": 1,
        "capability": "SCREEN_CLICK",
        "status": "ACCEPTED",
    }
    assert len(transport.calls) == 1
    assert transport.calls[0]["workflow"]["next_index"] == 1
    assert transport.calls[0]["workflow"]["state"] == "RUNNING"


def test_workflow_step_enqueue_rejects_invalid_step_without_persistence():
    transport = FakeTransport()
    workflow = {"id": "wf-2", "steps": [{"capability": "NOT_ALLOWED", "arguments": {}}], "state": "RUNNING", "next_index": 0}

    assert _enqueue_step({"device_id": "device-1"}, "owner-1", transport, index=0, workflow=workflow) is None
    assert transport.calls == []

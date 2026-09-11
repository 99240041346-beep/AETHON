from __future__ import annotations

from datetime import datetime, timezone

from aethon.android_command_transport import AndroidCommandTransport


class CasStore:
    def __init__(self):
        self.state = "PAUSED"
        self.command_id = "cmd-1"
        self.updates = 0

    def execute(self, query, params=()):
        q = " ".join(query.split()).lower()
        if q.startswith("update device_commands set arguments_json=jsonb_set"):
            state_json, owner, workflow_id, *expected = params
            state = __import__("json").loads(state_json)
            if expected and self.state != expected[0]:
                return []
            self.state = state
            self.updates += 1
            return [(self.command_id,)]
        if q.startswith("select command_id,owner_id,device_id,capability,status,arguments_json,issued_at"):
            return [(self.command_id, "owner-a", "phone-1", "SCREEN_READ", "ACCEPTED", {"_workflow": {"id": "wf-1", "state": self.state, "next_index": 1}}, datetime.now(timezone.utc))]
        if q.startswith("update device_commands set status='cancelled'"):
            return []
        raise AssertionError(q)


def transport():
    t = AndroidCommandTransport.__new__(AndroidCommandTransport)
    t.store = CasStore()
    return t


def test_concurrent_resume_only_one_pause_to_running_transition_wins():
    t = transport()
    first = t.set_workflow_state(workflow_id="wf-1", owner_id="owner-a", state="RUNNING")
    second = t.set_workflow_state(workflow_id="wf-1", owner_id="owner-a", state="RUNNING")
    assert first["workflow"]["state"] == "RUNNING"
    assert second is None
    assert t.store.updates == 1


def test_resume_is_not_allowed_to_restart_completed_workflow():
    t = transport()
    t.store.state = "COMPLETED"
    assert t.set_workflow_state(workflow_id="wf-1", owner_id="owner-a", state="RUNNING") is None
    assert t.store.updates == 0

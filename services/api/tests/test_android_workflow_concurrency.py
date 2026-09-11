from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from aethon.android_command_transport import AndroidCommandTransport, CommandTransportError


class CasStore:
    def __init__(self):
        self.state = "PAUSED"
        self.command_id = "cmd-1"
        self.updates = 0
        self.workflow_commands: dict[int, dict] = {}
        self.insert_calls = 0
        self.simulate_insert_race = False

    def execute(self, query, params=()):
        q = " ".join(query.split()).lower()
        if q.startswith("update device_commands set arguments_json=jsonb_set"):
            state_json, owner, workflow_id, *expected = params
            state = json.loads(state_json)
            if expected and self.state != expected[0]:
                return []
            self.state = state
            self.updates += 1
            return [(self.command_id,)]
        if q.startswith("select command_id,owner_id,device_id,capability,status,arguments_json,issued_at"):
            return [(self.command_id, "owner-a", "phone-1", "SCREEN_READ", "ACCEPTED", {"_workflow": {"id": "wf-1", "state": self.state, "next_index": 1}}, datetime.now(timezone.utc))]
        if q.startswith("select command_id,device_id,capability,status from device_commands"):
            step_index = int(params[2]) - 1
            row = self.workflow_commands.get(step_index)
            return [(row["command_id"], "phone-1", row["capability"], "ACCEPTED")] if row else []
        if q.startswith("select command_id,owner_id,device_id,capability,status,verified,error"):
            command_id = params[0]
            row = next((v for v in self.workflow_commands.values() if v["command_id"] == command_id), None)
            if not row:
                return []
            return [(command_id, "owner-a", "phone-1", row["capability"], "ACCEPTED", False, None, datetime.now(timezone.utc), datetime.now(timezone.utc), None, None, {"_workflow": {"id": "wf-1", "state": "RUNNING", "next_index": 1}}, None, None)]
        if q.startswith("insert into device_commands"):
            self.insert_calls += 1
            if self.simulate_insert_race:
                self.simulate_insert_race = False
                self.workflow_commands[0] = {"command_id": "cmd-raced", "capability": "SCREEN_READ"}
                raise RuntimeError("duplicate active workflow step")
            raise AssertionError("unexpected second workflow insert")
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


def test_workflow_step_insert_race_converges_on_existing_active_step():
    t = transport()
    t.store.state = "RUNNING"
    t.store.simulate_insert_race = True
    workflow = {"id": "wf-1", "state": "RUNNING", "next_index": 1, "steps": [{"capability": "SCREEN_READ", "arguments": {}}]}
    command = t.enqueue_workflow_step(owner_id="owner-a", device_id="phone-1", capability="SCREEN_READ", arguments={}, workflow=workflow)
    assert command.command_id == "cmd-raced"
    assert command.capability == "SCREEN_READ"
    assert t.store.insert_calls == 1


def test_workflow_step_pending_is_single_source_for_existing_active_step():
    t = transport()
    t.store.workflow_commands[0] = {"command_id": "cmd-existing", "capability": "SCREEN_CLICK"}
    workflow = {"id": "wf-1", "state": "RUNNING", "next_index": 1, "steps": [{"capability": "SCREEN_CLICK", "arguments": {}}]}
    command = t.enqueue_workflow_step(owner_id="owner-a", device_id="phone-1", capability="SCREEN_CLICK", arguments={}, workflow=workflow)
    assert command.command_id == "cmd-existing"


def test_workflow_step_requires_positive_next_index():
    t = transport()
    with pytest.raises(CommandTransportError):
        t.enqueue_workflow_step(owner_id="owner-a", device_id="phone-1", capability="SCREEN_READ", arguments={}, workflow={"id": "wf-1", "next_index": 0})

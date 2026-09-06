from aethon.agent_state import AgentState, AgentStateStore


def test_agent_state_round_trips(tmp_path):
    store = AgentStateStore(str(tmp_path / "state.db"))
    state = AgentState(
        task_id="task-1",
        plan={"revision": 2, "steps": [{"id": "step-1", "status": "SUCCEEDED"}]},
        observations=["step-1: completed"],
        approvals=[{"tool": "publish", "approved": True}],
        recovery_history=[{"strategy": "alternative_tool"}],
        last_verified_step="step-1",
        status="PAUSED",
    )
    store.save(state)
    restored = store.load("task-1")
    assert restored is not None
    assert restored.last_verified_step == "step-1"
    assert restored.plan["revision"] == 2
    assert restored.recovery_history[0]["strategy"] == "alternative_tool"


def test_missing_state_returns_none(tmp_path):
    store = AgentStateStore(str(tmp_path / "state.db"))
    assert store.load("missing") is None

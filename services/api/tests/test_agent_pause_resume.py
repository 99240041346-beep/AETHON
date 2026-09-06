import tempfile
from pathlib import Path

from aethon.agent import AgentRuntime
from aethon.agent_state import AgentStateStore
from aethon.schemas import Task, TaskStatus


def test_agent_pauses_at_checkpoint_and_resumes_from_persisted_state():
    with tempfile.TemporaryDirectory() as tmp:
        state_path = str(Path(tmp) / "agent_state.db")
        state_store = AgentStateStore(state_path)
        task = Task(goal="resume this task after a pause")

        state_store.request_pause(task.task_id)
        first = AgentRuntime(state_store=state_store).run(task)

        assert first.status == TaskStatus.PAUSED
        saved = state_store.load(task.task_id)
        assert saved is not None
        assert saved.status == "PAUSED"
        assert saved.plan["steps"]
        assert saved.last_verified_step is None

        restarted_store = AgentStateStore(state_path)
        assert restarted_store.load(task.task_id) is not None
        restarted_store.clear_pause(task.task_id)
        resumed = AgentRuntime(state_store=restarted_store).run(first)

        assert resumed.status == TaskStatus.SUCCEEDED
        assert resumed.result is not None
        final_state = restarted_store.load(task.task_id)
        assert final_state is not None
        assert final_state.status == "SUCCEEDED"
        assert final_state.last_verified_step is not None


def test_pause_request_is_durable_across_state_store_instances():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "agent_state.db")
        task = Task(goal="pause control")
        first = AgentStateStore(path)
        first.request_pause(task.task_id)

        second = AgentStateStore(path)
        assert second.pause_requested(task.task_id) is True
        second.clear_pause(task.task_id)
        assert second.pause_requested(task.task_id) is False

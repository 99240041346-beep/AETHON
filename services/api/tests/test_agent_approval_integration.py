from pathlib import Path

from aethon.agent_brain import AgentBrain, Plan, PlanStep, StepKind
from aethon.agent_state import AgentStateStore
from aethon.agent import AgentRuntime
from aethon.schemas import RiskClass, Task, ToolResult, ToolSpec


class HighRiskToolRegistry:
    def __init__(self):
        self.calls = 0
        self.spec = ToolSpec(name="write_file", description="test side-effecting tool", risk=RiskClass.HIGH, side_effects=True)

    def list(self):
        return [self.spec]

    def execute(self, request):
        self.calls += 1
        return ToolResult(ok=True, output="written")


class OneToolBrain(AgentBrain):
    def initial_plan(self, goal, tool_names=None):
        return Plan(goal, [PlanStep("step-1", "perform approved write", StepKind.TOOL, "write_file", {"path": "x"})])


def test_runtime_pauses_for_approval_without_replanning(tmp_path: Path):
    store = AgentStateStore(str(tmp_path / "state.db"))
    tools = HighRiskToolRegistry()
    runtime = AgentRuntime(brain=OneToolBrain(), tools=tools, state_store=store)
    task = Task(goal="perform approved write")

    paused = runtime.run(task)

    assert paused.status.value == "AWAITING_APPROVAL"
    assert tools.calls == 0
    assert store.load(task.task_id).approvals[0]["status"] == "PENDING"
    assert not any(event.type == "plan.replanned" for event in runtime.events[task.task_id])


def test_runtime_approval_resumes_after_restart_and_consumes_once(tmp_path: Path):
    store = AgentStateStore(str(tmp_path / "state.db"))
    tools = HighRiskToolRegistry()
    first = AgentRuntime(brain=OneToolBrain(), tools=tools, state_store=store)
    task = Task(goal="perform approved write")

    paused = first.run(task)
    assert paused.status.value == "AWAITING_APPROVAL"
    first.approve(task.task_id, "step-1", "operator")

    second = AgentRuntime(brain=OneToolBrain(), tools=tools, state_store=store)
    resumed = second.run(task)

    assert resumed.status.value == "SUCCEEDED"
    assert tools.calls == 1
    assert store.load(task.task_id).approvals == []
    assert any(event.type == "approval.consumed" for event in second.events[task.task_id])
    assert not any(event.type == "plan.replanned" for event in second.events[task.task_id])

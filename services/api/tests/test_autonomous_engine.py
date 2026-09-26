from aethon.autonomous_engine import AutonomousAgentEngine, Checkpoint
from aethon.astra_core import AgentDefinition, Permission, PlanStep, ToolRegistry, ToolSpec, RunStatus


def make_engine():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("one", "one", Permission.READ, {"type": "object", "properties": {}}),
        lambda: "first",
    )
    registry.register(
        ToolSpec("two", "two", Permission.READ, {"type": "object", "properties": {}}),
        lambda: "second",
    )
    return registry


def definition():
    return AgentDefinition(
        "test", "Test", "bounded", permissions=(Permission.READ,),
        max_steps=4, max_tool_calls=4, max_retries=1,
    )


def test_autonomous_engine_respects_dependencies_and_checkpoints():
    saved = []
    engine = AutonomousAgentEngine(tools=make_engine(), checkpoint_sink=saved.append)
    run, plan = engine.build(
        goal="complete workflow",
        agent_id="test",
        run_id="r1",
        steps=[
            PlanStep("one", "first", tool="one"),
            PlanStep("two", "second", depends_on=("one",), tool="two"),
        ],
    )
    result = engine.execute(run=run, definition=definition(), plan=plan, granted={Permission.READ})
    assert result.run.status is RunStatus.COMPLETED
    assert result.plan.outputs == {"one": "first", "two": "second"}
    assert len(saved) == 3


def test_autonomous_engine_pauses_for_external_confirmation():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("external", "external", Permission.EXTERNAL_ACTION, {"type": "object", "properties": {}}),
        lambda: "done",
    )
    engine = AutonomousAgentEngine(tools=registry)
    run, plan = engine.build(
        goal="external action", agent_id="test", run_id="r2",
        steps=[PlanStep("external", "external", tool="external")],
    )
    result = engine.execute(
        run=run, definition=definition(), plan=plan,
        granted={Permission.EXTERNAL_ACTION},
    )
    assert result.run.status is RunStatus.WAITING_CONFIRMATION
    assert result.plan.outputs == {}


def test_autonomous_engine_can_resume_from_checkpoint():
    engine = AutonomousAgentEngine(tools=make_engine())
    run, plan = engine.build(
        goal="resume", agent_id="test", run_id="r3",
        steps=[
            PlanStep("one", "first", tool="one"),
            PlanStep("two", "second", depends_on=("one",), tool="two"),
        ],
    )
    checkpoint = Checkpoint("r3", ("one",), {"one": "first"}, "running")
    result = engine.execute(
        run=run, definition=definition(), plan=plan,
        granted={Permission.READ}, resume=checkpoint,
    )
    assert result.run.status is RunStatus.COMPLETED
    assert result.plan.outputs["two"] == "second"

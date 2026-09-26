from aethon.astra_core import (
    ASTRAOrchestrator, AgentDefinition, AgentRun, Permission, PlanStep,
    RecoveryManager, RunStatus, ToolRegistry, ToolSpec,
)


def test_tool_registry_rejects_unknown_arguments_and_enforces_permission():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("read", "read value", Permission.READ,
                 input_schema={"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}),
        lambda key: key,
    )
    try:
        registry.execute("read", {"key": "x", "extra": 1}, granted={Permission.READ})
        assert False
    except ValueError:
        pass
    assert registry.execute("read", {"key": "x"}, granted={Permission.READ}) == "x"


def test_external_action_requires_confirmation():
    registry = ToolRegistry()
    registry.register(ToolSpec("send", "send", Permission.EXTERNAL_ACTION), lambda: "sent")
    try:
        registry.execute("send", {}, granted={Permission.EXTERNAL_ACTION})
        assert False
    except PermissionError:
        pass
    assert registry.execute("send", {}, granted={Permission.EXTERNAL_ACTION}, confirmed=True) == "sent"


def test_agent_run_is_bounded():
    definition = AgentDefinition("a", "Agent", "test", max_steps=1, max_tool_calls=1)
    run = AgentRun("r", "a", "goal")
    run.start()
    run.steps = 1
    try:
        run.check_limits(definition)
        assert False
    except RuntimeError:
        pass


def test_plan_dependencies_are_validated():
    planner = ASTRAOrchestrator().planner
    plan = planner.create("goal", [PlanStep("a", "first"), PlanStep("b", "second", ("a",))])
    assert plan.next_ready(set()).id == "a"
    assert plan.next_ready({"a"}).id == "b"


def test_recovery_is_bounded():
    recovery = RecoveryManager()
    assert recovery.should_retry(TimeoutError("timeout"), 0, 2)
    assert not recovery.should_retry(TimeoutError("timeout"), 2, 2)

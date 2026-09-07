def test_17l_context_cannot_create_unregistered_tools():
    from app.agent_brain import AgentBrain
    from app.decision_context import DecisionContextBuilder
    plan = AgentBrain().initial_plan("Explain this", set(), DecisionContextBuilder().build(["research"]).memories)
    assert all(step.tool is None for step in plan.steps)

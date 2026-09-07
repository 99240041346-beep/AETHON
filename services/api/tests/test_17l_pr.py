def test_17l_planning_context_is_bounded_and_tool_gated():
    from app.agent_brain import AgentBrain
    from app.decision_context import DecisionContextBuilder

    context = DecisionContextBuilder(max_items=5, max_chars=100).build(["research"])
    plan = AgentBrain().initial_plan("Explain this", {"web_search"}, context.memories)
    assert plan.steps[0].tool == "web_search"
    assert len(plan.decision_context) <= 5

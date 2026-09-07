def test_17l_final_smoke():
    from app.agent_brain import AgentBrain
    from app.decision_context import DecisionContextBuilder
    context = DecisionContextBuilder().build(["research"])
    plan = AgentBrain().initial_plan("Explain this", {"web_search"}, context.memories)
    assert plan.steps[0].tool == "web_search"

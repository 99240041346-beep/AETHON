def test_17l_submit_smoke():
    from app.agent_brain import AgentBrain
    from app.decision_context import DecisionContextBuilder
    plan = AgentBrain().initial_plan("Explain this", {"web_search"}, DecisionContextBuilder().build(["research"]).memories)
    assert plan.steps[0].tool == "web_search"

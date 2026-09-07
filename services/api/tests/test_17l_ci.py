def test_17l_decision_loop_smoke():
    from app.agent_brain import AgentBrain
    from app.decision_context import DecisionContextBuilder

    context = DecisionContextBuilder().build(["Prior research suggests fresh public research is needed."])
    plan = AgentBrain().initial_plan("Explain the topic", {"web_search"}, context.memories)
    assert plan.steps[0].tool == "web_search"
    assert len(plan.decision_context) <= 5

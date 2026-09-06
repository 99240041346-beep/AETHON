from aethon.agent_brain import AgentBrain


def test_search_goal_gets_tool_plan():
    brain = AgentBrain()
    plan = brain.initial_plan("find the latest AETHON architecture", {"web_search"})
    assert plan.steps[0].tool == "web_search"
    assert plan.steps[1].depends_on == ["step-1"]


def test_dependencies_block_execution_until_success():
    brain = AgentBrain()
    plan = brain.initial_plan("answer this")
    plan.steps[0].status = "PENDING"
    plan.steps[1].status = "PENDING"
    assert brain.next_decision(plan).step.step_id == "step-1"
    brain.record_success(plan, "step-1")
    assert brain.next_decision(plan).step.step_id == "step-2"


def test_failure_replans_with_bounded_retry():
    brain = AgentBrain(max_replans=2)
    plan = brain.initial_plan("answer this")
    decision = brain.record_failure(plan, "step-1", "temporary failure")
    assert decision.action == "REPLAN"
    assert plan.revision == 1
    decision = brain.record_failure(plan, "step-1", "temporary failure")
    assert decision.action == "FAIL"


def test_plan_budget_is_enforced():
    brain = AgentBrain(max_steps=1)
    plan = brain.initial_plan("answer this")
    assert len(plan.steps) == 1

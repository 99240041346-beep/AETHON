from aethon.agent_brain import AgentBrain, FailureClass, StepKind
from aethon.decision_context import DecisionContextBuilder


def test_search_goal_gets_tool_plan():
    brain = AgentBrain()
    plan = brain.initial_plan("find the latest AETHON architecture", {"web_search", "web_fetch"})
    assert plan.steps[0].tool == "web_search"
    assert plan.steps[1].depends_on == ["step-1"]
    assert plan.steps[2].kind == StepKind.VERIFY


def test_memory_context_can_trigger_bounded_research_plan():
    brain = AgentBrain()
    context = DecisionContextBuilder(max_items=5, max_chars=4000).build(["Prior research indicates this topic needs fresh public research."])
    plan = brain.initial_plan("explain the topic", {"web_search"}, context.memories)
    assert plan.steps[0].tool == "web_search"
    assert plan.decision_context == context.memories
    assert len(plan.decision_context) <= 5


def test_non_research_memory_does_not_change_simple_plan():
    brain = AgentBrain()
    plan = brain.initial_plan("answer this", {"web_search"}, ("A normal historical note.",))
    assert plan.steps[0].kind == StepKind.REASON
    assert plan.steps[0].tool is None


def test_dependencies_block_execution_until_success():
    brain = AgentBrain()
    plan = brain.initial_plan("answer this")
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


def test_replan_switches_to_alternative_tool_when_possible():
    brain = AgentBrain()
    plan = brain.initial_plan("find current information", {"web_search", "web_fetch"})
    plan.steps[0].arguments = {"url": "https://example.com"}
    decision = brain.replan(
        plan, "step-1", "web search failed: connection timeout",
        available_tools={"web_search", "web_fetch"},
    )
    assert decision.action == "REPLAN"
    assert plan.steps[0].tool == "web_fetch"
    assert plan.recovery_history[-1]["strategy"] == "alternative_tool"


def test_replan_regenerates_failed_candidate_and_preserves_completed_state():
    brain = AgentBrain()
    plan = brain.initial_plan("answer this")
    brain.record_success(plan, "step-1")
    decision = brain.next_decision(plan)
    assert decision.step.step_id == "step-2"
    brain.record_success(plan, "step-2")
    decision = brain.replan(plan, "step-3", "verification failed: insufficient evidence")
    assert decision.action == "REPLAN"
    assert "step-1" in plan.completed_steps
    assert "step-2" in plan.completed_steps
    assert plan.steps[1].status == "PENDING"
    assert plan.recovery_history[-1]["strategy"] == "regenerate_candidate"


def test_failure_classification():
    assert brain_failure("connection timeout") == FailureClass.TRANSIENT
    assert brain_failure("tool not found") == FailureClass.TOOL_UNAVAILABLE
    assert brain_failure("approval required for tool") == FailureClass.AUTHORIZATION
    assert brain_failure("invalid query") == FailureClass.INVALID_INPUT
    assert brain_failure("verification failed") == FailureClass.VERIFICATION


def brain_failure(reason):
    return AgentBrain.classify_failure(reason)

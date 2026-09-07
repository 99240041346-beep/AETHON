from app.agent_brain import AgentBrain, StepKind
from app.decision_context import DecisionContextBuilder


class Memory:
    def __init__(self, content):
        self.content = content


def test_memory_context_can_trigger_bounded_research_plan():
    context = DecisionContextBuilder().build([Memory("Prior context: research sources are needed")])
    plan = AgentBrain().initial_plan("Explain the topic", {"web_search"}, context.memories)
    assert plan.decision_context == context.memories
    assert plan.steps[0].kind == StepKind.TOOL
    assert plan.steps[0].tool == "web_search"


def test_context_never_grants_missing_tool():
    context = DecisionContextBuilder().build([Memory("research")])
    plan = AgentBrain().initial_plan("Explain the topic", set(), context.memories)
    assert all(step.tool is None for step in plan.steps)
    assert [step.kind for step in plan.steps] == [StepKind.REASON, StepKind.VERIFY]


def test_context_is_bounded_in_plan():
    context = DecisionContextBuilder(max_items=5, max_chars=100).build([Memory("x" * 500)])
    plan = AgentBrain().initial_plan("Explain", {"web_search"}, context.memories)
    assert len(plan.decision_context) == 1
    assert len(plan.decision_context[0]) == 100

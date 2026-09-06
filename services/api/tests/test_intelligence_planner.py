from aethon.agent_brain import AgentBrain, StepKind
from aethon.planner import IntelligencePlanner


class FakeModel:
    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response


def test_model_plan_is_parsed_and_bounded():
    model = FakeModel('{"steps":[{"step_id":"s1","description":"research","kind":"TOOL","tool":"web_search","arguments":{"query":"x"},"depends_on":[]},{"step_id":"s2","description":"answer","kind":"REASON","tool":null,"arguments":{},"depends_on":["s1"]}]}')
    plan = IntelligencePlanner(model, AgentBrain(max_steps=4)).create_plan("research x", {"web_search"})
    assert [s.kind for s in plan.steps] == [StepKind.TOOL, StepKind.REASON, StepKind.VERIFY]
    assert plan.steps[0].tool == "web_search"


def test_unknown_model_tool_is_downgraded_to_reasoning():
    model = FakeModel('{"steps":[{"step_id":"s1","description":"do it","kind":"TOOL","tool":"dangerous_unknown","arguments":{},"depends_on":[]}]}')
    plan = IntelligencePlanner(model).create_plan("do it", {"web_search"})
    assert plan.steps[0].kind == StepKind.REASON
    assert plan.steps[0].tool is None


def test_invalid_model_output_uses_existing_brain_fallback():
    model = FakeModel("not json")
    plan = IntelligencePlanner(model).create_plan("latest news", {"web_search"})
    assert plan.steps[0].tool == "web_search"
    assert plan.steps[-1].kind == StepKind.VERIFY

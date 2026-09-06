from aethon.agent import AgentRuntime
from aethon.agent_brain import AgentBrain
from aethon.schemas import Task, TaskStatus
from aethon.verification import VerificationResult


class Model:
    name = 'test-model'

    def __init__(self):
        self.prompts = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return 'candidate answer'

    def health(self) -> bool:
        return True


class PassingVerifier:
    def verify(self, goal, result):
        return VerificationResult(True, 'passed', {'source': 'test'})


class FailingOnceVerifier:
    def __init__(self):
        self.calls = 0

    def verify(self, goal, result):
        self.calls += 1
        if self.calls == 1:
            return VerificationResult(False, 'evidence incomplete', {})
        return VerificationResult(True, 'passed after replan', {})


def test_runtime_emits_plan_and_tool_observation_events():
    runtime = AgentRuntime(verifier=PassingVerifier())
    model = Model()
    runtime.models = model
    task = runtime.run(Task(goal='search for the latest AETHON architecture'))
    events = runtime.events[task.task_id]
    types = [event.type for event in events]
    assert task.status == TaskStatus.SUCCEEDED
    assert 'plan.created' in types
    assert 'tool.authorization' in types
    assert 'tool.observed' in types
    assert 'plan.step.completed' in types
    assert any(event.data.get('step_id') == 'step-2' for event in events if event.type == 'verification.completed')


def test_runtime_replans_after_verification_failure_with_bounded_retry():
    runtime = AgentRuntime(verifier=FailingOnceVerifier(), brain=AgentBrain(max_steps=4, max_replans=2))
    model = Model()
    runtime.models = model
    task = runtime.run(Task(goal='give a concise answer'))
    events = runtime.events[task.task_id]
    assert task.status == TaskStatus.SUCCEEDED
    replans = [event for event in events if event.type == 'plan.replanned']
    assert len(replans) == 1
    assert replans[0].data['revision'] == 1


def test_runtime_blocks_when_replan_budget_is_exhausted():
    class AlwaysFail:
        def verify(self, goal, result):
            return VerificationResult(False, 'never verified', {})

    runtime = AgentRuntime(verifier=AlwaysFail(), brain=AgentBrain(max_steps=4, max_replans=0))
    runtime.models = Model()
    task = runtime.run(Task(goal='answer a question'))
    assert task.status == TaskStatus.BLOCKED
    assert task.error == 'execution budget exhausted' or 'replan budget exhausted' in (task.error or '')

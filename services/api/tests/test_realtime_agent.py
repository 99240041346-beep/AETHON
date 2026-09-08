import pytest

from app.realtime_agent import BoundedRealtimeAgent, RealtimeOperation, RealtimeRequest, RealtimeResult, RealtimeSecurityError


class Adapter:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def execute(self, request):
        self.calls.append(request)
        return RealtimeResult(request.operation, not self.fail, error="failed" if self.fail else "")


def test_channel_and_payload_requirements():
    agent = BoundedRealtimeAgent()
    with pytest.raises(RealtimeSecurityError):
        agent.validate_requests([RealtimeRequest(RealtimeOperation.PUBLISH, channel="", payload="x")])
    with pytest.raises(RealtimeSecurityError):
        agent.validate_requests([RealtimeRequest(RealtimeOperation.PUBLISH, channel="events")])


def test_approval_gate_prevents_adapter_execution():
    adapter = Adapter()
    results = BoundedRealtimeAgent().execute(
        [RealtimeRequest(RealtimeOperation.SEND, channel="events", payload="hello", requires_approval=True)], adapter
    )
    assert results[0].error == "approval required"
    assert not adapter.calls


def test_failed_operation_stops_sequence():
    adapter = Adapter(fail=True)
    results = BoundedRealtimeAgent().execute(
        [RealtimeRequest(RealtimeOperation.PUBLISH, channel="events", payload="x"), RealtimeRequest(RealtimeOperation.CLOSE)], adapter
    )
    assert len(results) == 1
    assert len(adapter.calls) == 1


def test_operation_and_payload_budgets_are_bounded():
    agent = BoundedRealtimeAgent(max_operations=1, max_payload=2)
    with pytest.raises(RealtimeSecurityError):
        agent.validate_requests([RealtimeRequest(RealtimeOperation.CLOSE), RealtimeRequest(RealtimeOperation.CLOSE)])
    with pytest.raises(RealtimeSecurityError):
        agent.validate_requests([RealtimeRequest(RealtimeOperation.PUBLISH, channel="x", payload="123")])


def test_plan_is_conservative_and_requires_goal():
    agent = BoundedRealtimeAgent()
    assert agent.plan("live updates")[0].operation is RealtimeOperation.CLOSE
    with pytest.raises(RealtimeSecurityError):
        agent.plan(" ")

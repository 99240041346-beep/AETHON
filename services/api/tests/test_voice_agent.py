import pytest

from app.voice_agent import BoundedVoiceAgent, VoiceOperation, VoiceRequest, VoiceResult, VoiceSecurityError


class Adapter:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def execute(self, request):
        self.calls.append(request)
        if self.fail:
            return VoiceResult(request.operation, False, error="failed")
        return VoiceResult(request.operation, True, text="ok")


def test_transcription_requires_audio_and_synthesis_requires_text():
    agent = BoundedVoiceAgent()
    with pytest.raises(VoiceSecurityError):
        agent.validate_requests([VoiceRequest(VoiceOperation.TRANSCRIBE)])
    with pytest.raises(VoiceSecurityError):
        agent.validate_requests([VoiceRequest(VoiceOperation.SYNTHESIZE)])


def test_approval_gate_prevents_adapter_execution():
    adapter = Adapter()
    result = BoundedVoiceAgent().execute(
        [VoiceRequest(VoiceOperation.SYNTHESIZE, text="hello", requires_approval=True)], adapter
    )
    assert result[0].error == "approval required"
    assert not adapter.calls


def test_failed_operation_stops_sequence():
    adapter = Adapter(fail=True)
    results = BoundedVoiceAgent().execute(
        [VoiceRequest(VoiceOperation.SYNTHESIZE, text="hello"), VoiceRequest(VoiceOperation.STOP)], adapter
    )
    assert len(results) == 1
    assert len(adapter.calls) == 1


def test_audio_and_operation_budgets_are_bounded():
    agent = BoundedVoiceAgent(max_operations=1, max_audio_bytes=2)
    with pytest.raises(VoiceSecurityError):
        agent.validate_requests([
            VoiceRequest(VoiceOperation.STOP), VoiceRequest(VoiceOperation.STOP)
        ])
    with pytest.raises(VoiceSecurityError):
        agent.validate_requests([VoiceRequest(VoiceOperation.TRANSCRIBE, audio=b"123")])


def test_plan_is_conservative_and_requires_goal():
    agent = BoundedVoiceAgent()
    assert agent.plan("voice interaction")[0].operation is VoiceOperation.STOP
    with pytest.raises(VoiceSecurityError):
        agent.plan(" ")

def test_integrated_milestone_imports():
    from aethon.voice_api import VoiceRequest
    from aethon.device_gateway import DeviceGateway
    assert VoiceRequest(transcript="hello").language == "te-IN"
    assert DeviceGateway is not None

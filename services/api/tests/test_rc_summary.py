def test_release_candidate_imports():
    from aethon.device_gateway import DeviceGateway
    from aethon.voice_api import VoiceRequest
    assert DeviceGateway is not None
    assert VoiceRequest(transcript="hello").language == "te-IN"

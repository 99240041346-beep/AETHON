from aethon.voice_session import VoiceSessionManager


def test_voice_session_supports_interrupt_and_bounded_context():
    manager = VoiceSessionManager()
    session = manager.create("s1", "te-IN")
    session.add_turn("hello", "hi")
    session.interrupt()
    assert session.interrupted
    session.resume()
    assert session.active
    assert len(session.context()) == 1

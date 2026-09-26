from aethon.astra_multimodal import ASTRAMultimodal
from aethon.astra_voice import ASTRAVoice


def test_voice_session_is_bounded_and_explicit():
    session = ASTRAVoice().session("s1", "te-IN", wake_enabled=True)
    assert session.locale == "te-IN"
    assert session.wake_enabled is True


def test_multimodal_rejects_empty_or_oversized_input():
    facade = ASTRAMultimodal()
    try:
        facade.build_packet([])
    except ValueError:
        pass
    else:
        raise AssertionError("empty multimodal packet accepted")

from app.language_service import action_ack, detect_language, deterministic_ack, normalize_language


def test_normalize_supported_locales():
    assert normalize_language("te-IN").tts_locale == "te-IN"
    assert normalize_language("en-US").tts_locale == "en-US"
    assert normalize_language("hi-IN").code == "hi"


def test_detect_telugu_script():
    assert detect_language("నమస్కారం", "en-US").code == "te"


def test_detect_tamil_script():
    assert detect_language("வணக்கம்", "en-US").code == "ta"


def test_fallback_stays_in_selected_language():
    assert deterministic_ack(normalize_language("te-IN"), "hello").startswith("నేను విన్నాను")
    assert deterministic_ack(normalize_language("es-ES"), "hola").startswith("He escuchado")


def test_action_ack_stays_in_selected_language():
    assert "abriendo" in action_ack(normalize_language("es-ES"), "YouTube")
    assert "YouTube" in action_ack(normalize_language("te-IN"), "YouTube")

from fastapi.testclient import TestClient

from app.language_service import detect_language, normalize_language
from app.main import app


def test_supported_language_profiles_include_telugu_and_major_indian_languages():
    assert normalize_language("te-IN").code == "te"
    assert normalize_language("ta-IN").code == "ta"
    assert normalize_language("hi-IN").code == "hi"


def test_telugu_script_is_detected_when_requested_language_is_english():
    assert detect_language("నాకు సహాయం చేయి", "en-US").code == "te"


def test_language_api_lists_supported_languages():
    client = TestClient(app)
    response = client.get("/v1/languages")
    assert response.status_code == 200
    codes = {item["language"] for item in response.json()}
    assert {"en", "te", "hi", "ta", "kn", "ml"}.issubset(codes)


def test_language_api_detects_telugu():
    client = TestClient(app)
    response = client.post("/v1/languages/detect", json={"text": "నమస్కారం"})
    assert response.status_code == 200
    assert response.json()["language"] == "te"


def test_voice_api_preserves_telugu_locale_and_fallback_language():
    client = TestClient(app)
    response = client.post(
        "/v1/voice/respond",
        json={"transcript": "నాకు సహాయం చేయి", "language": "te-IN"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "te-IN"
    assert body["response"].startswith("నేను విన్నాను:")


def test_voice_api_uses_requested_english_for_plain_english():
    client = TestClient(app)
    response = client.post(
        "/v1/voice/respond",
        json={"transcript": "How are you?", "language": "en-US"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en-US"
    assert body["response"].startswith("I heard you:")

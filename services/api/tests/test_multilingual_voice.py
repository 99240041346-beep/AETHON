from fastapi.testclient import TestClient

from app.language_service import detect_language, normalize_language
from app.main import app


def test_language_normalization():
    assert normalize_language("te-IN").code == "te"
    assert normalize_language("en-US").code == "en"
    assert normalize_language("hi-IN").code == "hi"


def test_telugu_script_detection():
    assert detect_language("నాకు సహాయం చేయి", "en-US").code == "te"


def test_language_api_lists_languages():
    response = TestClient(app).get("/v1/languages")
    assert response.status_code == 200
    codes = {item["language"] for item in response.json()}
    assert {"en", "te", "hi", "ta", "kn", "ml"}.issubset(codes)


def test_language_api_detects_telugu():
    response = TestClient(app).post("/v1/languages/detect", json={"text": "నమస్కారం"})
    assert response.status_code == 200
    assert response.json()["language"] == "te"


def test_voice_telugu_fallback():
    response = TestClient(app).post("/v1/voice/respond", json={"transcript": "నాకు సహాయం చేయి", "language": "te-IN"})
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "te-IN"
    assert body["response"].startswith("నేను విన్నాను:")


def test_voice_english_fallback():
    response = TestClient(app).post("/v1/voice/respond", json={"transcript": "How are you?", "language": "en-US"})
    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en-US"
    assert body["response"].startswith("I heard you:")

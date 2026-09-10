from fastapi.testclient import TestClient

from app.main import app


def test_multilingual_language_api_and_voice_contracts():
    client = TestClient(app)
    languages = client.get('/v1/languages')
    assert languages.status_code == 200
    assert any(item['language'] == 'te' for item in languages.json())

    detected = client.post('/v1/languages/detect', json={'text': 'నాకు సహాయం చేయి'})
    assert detected.status_code == 200
    assert detected.json()['language'] == 'te'

    voice = client.post('/v1/voice/respond', json={'transcript': 'నమస్కారం', 'language': 'te-IN'})
    assert voice.status_code == 200
    assert voice.json()['language'] == 'te-IN'
    assert voice.json()['response'].startswith('నేను విన్నాను:')

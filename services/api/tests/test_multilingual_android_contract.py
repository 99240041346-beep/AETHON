from pathlib import Path


def test_android_client_uses_utf8_and_unified_assistant_endpoint():
    source = Path(__file__).resolve().parents[3] / 'android' / 'app' / 'src' / 'main' / 'java' / 'ai' / 'aethon' / 'android' / 'MainActivity.java'
    text = source.read_text(encoding='utf-8')
    assert '/v1/assistant/respond' in text
    assert 'StandardCharsets.UTF_8' in text
    assert 'responseLocale' in text

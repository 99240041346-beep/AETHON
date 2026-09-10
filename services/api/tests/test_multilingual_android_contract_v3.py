from pathlib import Path


def test_android_multilingual_transport_contract():
    root = Path(__file__).resolve().parents[3]
    source = root / 'android' / 'app' / 'src' / 'main' / 'java' / 'ai' / 'aethon' / 'android' / 'MainActivity.java'
    text = source.read_text(encoding='utf-8')
    assert '/v1/assistant/respond' in text
    assert 'StandardCharsets.UTF_8' in text
    assert 'responseLocale' in text
    assert 'setLanguage(locale)' in text

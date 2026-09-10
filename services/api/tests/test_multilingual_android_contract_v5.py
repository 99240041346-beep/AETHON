from pathlib import Path


def test_android_assistant_endpoint_contract():
    root = Path(__file__).resolve().parents[3]
    source = root / 'android' / 'app' / 'src' / 'main' / 'java' / 'ai' / 'aethon' / 'android' / 'MainActivity.java'
    assert '/v1/assistant/respond' in source.read_text(encoding='utf-8')

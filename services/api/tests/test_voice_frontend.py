from pathlib import Path


ROOT = Path(__file__).parents[1] / "app" / "static"


def test_voice_controls_are_wired():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="voiceBtn"' in html
    assert 'id="speakBtn"' in html
    assert "SpeechRecognition" in js
    assert "speechSynthesis" in js
    assert "speakResponse" in js
    assert ".voice-btn" in css

from pathlib import Path


APP_JS = Path(__file__).parents[1] / "app" / "static" / "app.js"


def test_frontend_splits_sse_records_on_real_newlines():
    source = APP_JS.read_text(encoding="utf-8")
    assert 'buffer.split("\\n\\n")' in source
    assert 'record.split("\\n")' in source
    assert 'buffer.split("\\\\n\\\\n")' not in source

from app.coding_api import CodingRequest, build_coding_prompt


def test_coding_prompt_includes_existing_code_and_error_for_debugging():
    prompt = build_coding_prompt(CodingRequest(
        request="Fix the failing parser",
        mode="debug",
        language="Python",
        code="def parse(x): return int(x)",
        error="ValueError: invalid literal",
    ))
    assert "MODE: debug" in prompt
    assert "EXISTING CODE:" in prompt
    assert "ERROR / LOGS:" in prompt
    assert "Never claim you created files" in prompt


def test_coding_prompt_supports_create_and_multifile_output():
    prompt = build_coding_prompt(CodingRequest(
        request="Create a REST API",
        mode="create",
        language="Python",
        framework="FastAPI",
    ))
    assert "complete, runnable code" in prompt
    assert "FastAPI" in prompt
    assert "file names" in prompt


def test_coding_request_rejects_unknown_fields():
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        CodingRequest(request="Write a function", unexpected=True)

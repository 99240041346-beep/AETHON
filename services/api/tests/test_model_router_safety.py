from aethon.model_router import DeterministicProvider


def test_deterministic_provider_does_not_echo_runtime_prompt():
    prompt = (
        "You are AETHON, a bounded personal AI assistant.\n"
        "Context:\nuser: Hi\nassistant: internal context\n"
        "Attachments:\n(none)\nUser: What can you do?"
    )
    response = DeterministicProvider().generate(prompt)
    assert "internal context" not in response
    assert "You are AETHON" not in response
    assert "Context:" not in response
    assert "What can you do?" in response

def test_deterministic_provider_handles_escaped_newline_prompt():
    prompt = "System text\\nContext: internal\\nUser: hello aethon"
    response = DeterministicProvider().generate(prompt)
    assert response.endswith("hello aethon")
    assert "System text" not in response
    assert "Context:" not in response


def test_deterministic_provider_prefers_explicit_user_text():
    prompt = "System instructions\\nContext: internal\\nUser: hello aethon"
    response = DeterministicProvider().generate(prompt, user_text="Hello you Don")
    assert response.endswith("Hello you Don")
    assert "System instructions" not in response
    assert "internal" not in response

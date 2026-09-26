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
import httpx
import pytest

from aethon.model_router import DeterministicProvider, ModelRouter, OpenAIResponsesProvider


def test_deterministic_provider():
    assert ModelRouter(DeterministicProvider()).generate("hello") == "Hello! I'm AETHON. How can I help you today?"
    assert "Today is" in ModelRouter(DeterministicProvider()).generate("date")


def test_unknown_provider_rejected(monkeypatch):
    monkeypatch.setenv("AETHON_MODEL_PROVIDER", "unknown")
    with pytest.raises(RuntimeError, match="unsupported model provider"):
        ModelRouter()


def test_openai_provider_requires_configuration(monkeypatch):
    monkeypatch.setenv("AETHON_MODEL_PROVIDER", "openai-compatible")
    monkeypatch.delenv("AETHON_MODEL_BASE_URL", raising=False)
    monkeypatch.delenv("AETHON_MODEL_NAME", raising=False)
    monkeypatch.delenv("AETHON_MODEL_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="required"):
        ModelRouter()


def test_responses_provider_extracts_output_text(monkeypatch):
    seen = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["json"] = kwargs["json"]
        return httpx.Response(200, json={"output_text": "Hello from AETHON"})

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = OpenAIResponsesProvider("https://api.openai.com/v1", "gpt-5.6-luna", "test-key", web_search=True)
    assert provider.generate("hello") == "Hello from AETHON"
    assert seen["url"].endswith("/responses")
    assert seen["json"]["model"] == "gpt-5.6-luna"
    assert seen["json"]["tools"] == [{"type": "web_search_preview"}]


def test_responses_provider_extracts_nested_text(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            200,
            json={"output": [{"content": [{"type": "output_text", "text": "Nested answer"}]}]},
        ),
    )
    provider = OpenAIResponsesProvider("https://api.openai.com/v1", "gpt-5.6-luna", "test-key")
    assert provider.generate("hello") == "Nested answer"


def test_openai_environment_defaults(monkeypatch):
    monkeypatch.setenv("AETHON_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("AETHON_MODEL_API_KEY", "test-key")
    monkeypatch.delenv("AETHON_MODEL_NAME", raising=False)
    monkeypatch.delenv("AETHON_MODEL_BASE_URL", raising=False)
    monkeypatch.setenv("AETHON_WEB_SEARCH", "true")

    router = ModelRouter()
    assert isinstance(router.provider, OpenAIResponsesProvider)
    assert router.provider.model == "gpt-5.6-luna"
    assert router.provider.base_url == "https://api.openai.com/v1"
    assert router.provider.web_search is True


def test_deterministic_provider_unknown_question_is_natural():
    response = DeterministicProvider().generate("", user_text="Explain quantum computing")
    assert "remote language model" not in response.lower()
    assert "deployment" not in response.lower()
    assert response


def test_local_intelligence_self_description_and_telugu():
    # Explicit provider keeps this test independent of deployment credentials.
    from aethon.model_router import LocalIntelligenceProvider
    provider = LocalIntelligenceProvider()
    assert "AETHON" in provider.generate("", user_text="tell about yourself")
    assert "తెలుగులో" in provider.generate("", user_text="can you talk in telugu")


def test_auto_provider_without_key_uses_local_intelligence(monkeypatch):
    monkeypatch.setenv("AETHON_MODEL_PROVIDER", "auto")
    monkeypatch.delenv("AETHON_MODEL_API_KEY", raising=False)
    router = ModelRouter()
    assert router.provider.name == "local-intelligence"


def test_openai_compatible_provider_uses_development_system_prompt_and_context(monkeypatch):
    from aethon.model_router import OpenAICompatibleProvider

    seen = {}

    def fake_post(url, **kwargs):
        seen["url"] = url
        seen["payload"] = kwargs["json"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "Plan first, then test."}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    provider = OpenAICompatibleProvider("https://api.groq.com/openai/v1", "test-model", "test-key")
    answer = provider.generate(
        "Conversation history: user asked to fix the existing FastAPI project.",
        user_text="Help me debug the API",
    )

    assert answer == "Plan first, then test."
    assert seen["url"].endswith("/chat/completions")
    messages = seen["payload"]["messages"]
    assert messages[0]["role"] == "system"
    assert "software engineering partner" in messages[0]["content"]
    assert messages[1]["role"] == "developer"
    assert "Conversation history" in messages[1]["content"]
    assert messages[2] == {"role": "user", "content": "Help me debug the API"}
    assert seen["payload"]["temperature"] == 0.2


def test_openai_compatible_provider_does_not_claim_tools_were_run():
    from aethon.model_router import OpenAICompatibleProvider

    prompt = OpenAICompatibleProvider._system_prompt()
    assert "unless verified by actual tool results" in prompt
    assert "preserve working behavior and architecture" in prompt

import httpx
import pytest

from aethon.model_router import DeterministicProvider, ModelRouter, OpenAIResponsesProvider


def test_deterministic_provider():
    assert ModelRouter(DeterministicProvider()).generate("hello") == "AETHON received: hello"


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

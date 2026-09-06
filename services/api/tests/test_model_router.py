import pytest

from aethon.model_router import DeterministicProvider, ModelRouter


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

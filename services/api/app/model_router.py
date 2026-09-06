from __future__ import annotations

import os
from typing import Protocol

import httpx


class ModelProvider(Protocol):
    name: str
    def generate(self, prompt: str) -> str: ...


class DeterministicProvider:
    name = "deterministic"

    def generate(self, prompt: str) -> str:
        return f"AETHON received: {prompt}"


class OpenAICompatibleProvider:
    """Provider for OpenAI-compatible chat-completions endpoints.

    Credentials are read only from the environment and are never included in
    prompts, logs, or persisted task state.
    """

    name = "openai-compatible"

    def __init__(self, base_url: str, model: str, api_key: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "messages": [{"role": "user", "content": prompt}]},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("model provider returned an invalid response") from exc


class ModelRouter:
    def __init__(self, provider: ModelProvider | None = None):
        self.provider = provider or self._from_environment()

    @staticmethod
    def _from_environment() -> ModelProvider:
        provider = os.getenv("AETHON_MODEL_PROVIDER", "deterministic").lower()
        if provider == "deterministic":
            return DeterministicProvider()
        if provider in {"openai", "openai-compatible"}:
            base_url = os.getenv("AETHON_MODEL_BASE_URL")
            model = os.getenv("AETHON_MODEL_NAME")
            api_key = os.getenv("AETHON_MODEL_API_KEY")
            if not all((base_url, model, api_key)):
                raise RuntimeError("AETHON_MODEL_BASE_URL, AETHON_MODEL_NAME and AETHON_MODEL_API_KEY are required")
            return OpenAICompatibleProvider(base_url, model, api_key)
        raise RuntimeError(f"unsupported model provider: {provider}")

    def generate(self, prompt: str) -> str:
        return self.provider.generate(prompt)

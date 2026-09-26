from __future__ import annotations

"""Provider-neutral AI and creation gateway for AETHON.

Providers are optional and configured by environment variables. The gateway never
pretends that an unconfigured service is available. External generation remains
an explicit, auditable operation.
"""

from dataclasses import dataclass
import os
import time
from typing import Any
import httpx


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    kind: str
    model: str
    configured: bool
    capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    model: str
    text: str
    live: bool
    metadata: dict[str, Any]


class AIProviderError(RuntimeError):
    pass


class AIProvider:
    def info(self) -> ProviderInfo:
        raise NotImplementedError

    def generate(self, prompt: str, user_text: str | None = None) -> ProviderResult:
        raise NotImplementedError


class OpenAICompatibleAIProvider(AIProvider):
    def __init__(self, provider_id: str, base_url: str, model: str, api_key: str,
                 capabilities: tuple[str, ...] = ("chat", "code")) -> None:
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.capabilities = capabilities

    def info(self) -> ProviderInfo:
        return ProviderInfo(self.provider_id, "openai-compatible", self.model, bool(self.api_key),
                            self.capabilities)

    def generate(self, prompt: str, user_text: str | None = None) -> ProviderResult:
        if not self.api_key:
            raise AIProviderError(f"provider not configured: {self.provider_id}")
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "messages": [
                {"role": "system", "content": "You are an AETHON provider. Do not claim external actions unless verified."},
                {"role": "user", "content": user_text or prompt},
            ]},
            timeout=45,
        )
        if response.status_code >= 400:
            raise AIProviderError(f"{self.provider_id} returned HTTP {response.status_code}")
        data = response.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError(f"{self.provider_id} returned an invalid response") from exc
        return ProviderResult(self.provider_id, self.model, str(text).strip(), True, {})


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash",
                 base_url: str = "https://generativelanguage.googleapis.com/v1beta") -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def info(self) -> ProviderInfo:
        return ProviderInfo("gemini", "gemini", self.model, bool(self.api_key),
                            ("chat", "code", "vision", "research"))

    def generate(self, prompt: str, user_text: str | None = None) -> ProviderResult:
        if not self.api_key:
            raise AIProviderError("provider not configured: gemini")
        response = httpx.post(
            f"{self.base_url}/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={"contents": [{"role": "user", "parts": [{"text": user_text or prompt}]}]},
            timeout=45,
        )
        if response.status_code >= 400:
            raise AIProviderError(f"gemini returned HTTP {response.status_code}")
        data = response.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "\n".join(str(part["text"]) for part in parts if isinstance(part, dict) and "text" in part)
        except (KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("gemini returned an invalid response") from exc
        if not text.strip():
            raise AIProviderError("gemini returned no text")
        return ProviderResult("gemini", self.model, text.strip(), True, {})


class AIProviderFabric:
    """Registry, routing and bounded fallback across independently configured AIs."""

    def __init__(self, providers: list[AIProvider] | None = None) -> None:
        self.providers = {p.info().id: p for p in (providers or self._environment_providers())}

    @staticmethod
    def _environment_providers() -> list[AIProvider]:
        result: list[AIProvider] = []
        openai_key = os.getenv("AETHON_OPENAI_API_KEY") or os.getenv("AETHON_MODEL_API_KEY", "")
        if openai_key:
            result.append(OpenAICompatibleAIProvider(
                "openai", os.getenv("AETHON_OPENAI_BASE_URL", "https://api.openai.com/v1"),
                os.getenv("AETHON_OPENAI_MODEL", os.getenv("AETHON_MODEL_NAME", "gpt-5.6-luna")),
                openai_key, ("chat", "code", "vision", "research"),
            ))
        gemini_key = os.getenv("AETHON_GEMINI_API_KEY", "")
        if gemini_key:
            result.append(GeminiProvider(gemini_key, os.getenv("AETHON_GEMINI_MODEL", "gemini-2.5-flash")))
        for provider_id in ("anthropic", "groq", "mistral", "xai", "deepseek", "openrouter"):
            key = os.getenv(f"AETHON_{provider_id.upper()}_API_KEY", "")
            base = os.getenv(f"AETHON_{provider_id.upper()}_BASE_URL", "")
            model = os.getenv(f"AETHON_{provider_id.upper()}_MODEL", "")
            if key and base and model:
                result.append(OpenAICompatibleAIProvider(provider_id, base, model, key))
        return result

    def list(self) -> list[ProviderInfo]:
        return [provider.info() for provider in self.providers.values()]

    def get(self, provider_id: str) -> AIProvider:
        try:
            return self.providers[provider_id]
        except KeyError as exc:
            raise AIProviderError(f"unknown or unconfigured provider: {provider_id}") from exc

    def generate(self, prompt: str, user_text: str | None = None,
                 provider: str | None = None) -> ProviderResult:
        if provider:
            return self.get(provider).generate(prompt, user_text)
        errors: list[str] = []
        for candidate in self.providers.values():
            try:
                return candidate.generate(prompt, user_text)
            except (AIProviderError, httpx.HTTPError, OSError) as exc:
                errors.append(f"{candidate.info().id}: {type(exc).__name__}")
                time.sleep(0.05)
        raise AIProviderError("no configured AI provider completed the request" + (f" ({'; '.join(errors)})" if errors else ""))

    def capabilities(self) -> dict[str, list[str]]:
        return {info.id: list(info.capabilities) for info in self.list()}

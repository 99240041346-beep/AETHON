from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Sequence

import httpx


class EmbeddingError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    dimension: int

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class DisabledEmbeddingProvider(EmbeddingProvider):
    """Explicit no-op provider used when semantic embeddings are not configured."""

    dimension = 1536

    def embed(self, text: str) -> list[float]:
        raise EmbeddingError("semantic embeddings are not configured")


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    """Embedding provider for OpenAI-compatible /embeddings APIs."""

    def __init__(self, base_url: str, model: str, api_key: str, dimension: int = 1536, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.dimension = dimension
        self.timeout = timeout

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingError("cannot embed empty text")
        try:
            response = httpx.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            vector = payload["data"][0]["embedding"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise EmbeddingError(f"embedding request failed: {exc}") from exc
        if not isinstance(vector, list) or len(vector) != self.dimension:
            raise EmbeddingError(f"embedding dimension mismatch: expected {self.dimension}")
        return [float(value) for value in vector]


def build_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("AETHON_EMBEDDING_PROVIDER", "disabled").strip().lower()
    if provider in {"", "disabled", "none"}:
        return DisabledEmbeddingProvider()
    if provider in {"openai", "openai-compatible", "compatible"}:
        base_url = os.getenv("AETHON_EMBEDDING_BASE_URL") or os.getenv("AETHON_MODEL_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("AETHON_EMBEDDING_MODEL", "text-embedding-3-small")
        api_key = os.getenv("AETHON_EMBEDDING_API_KEY") or os.getenv("AETHON_MODEL_API_KEY", "")
        if not api_key:
            raise EmbeddingError("AETHON_EMBEDDING_API_KEY or AETHON_MODEL_API_KEY is required")
        dimension = int(os.getenv("AETHON_EMBEDDING_DIMENSION", "1536"))
        return OpenAICompatibleEmbeddingProvider(base_url, model, api_key, dimension=dimension)
    raise EmbeddingError(f"unsupported embedding provider: {provider}")

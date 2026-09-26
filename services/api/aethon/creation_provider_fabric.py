from __future__ import annotations

"""Bounded bridge to external creation providers.

AETHON treats provider APIs as replaceable adapters. Credentials stay in the
deployment environment; user prompts are never used as credentials.
"""

from dataclasses import dataclass
import os
from typing import Any
import httpx


@dataclass(frozen=True)
class CreationProviderInfo:
    id: str
    capabilities: tuple[str, ...]
    configured: bool


@dataclass(frozen=True)
class CreationResult:
    provider: str
    capability: str
    status: str
    output: dict[str, Any]


class CreationProviderFabric:
    def __init__(self, providers: dict[str, dict[str, Any]] | None = None) -> None:
        self.providers = providers or self._from_environment()

    @staticmethod
    def _from_environment() -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for provider_id in ("higgsfield", "canva", "vercel", "render"):
            prefix = f"AETHON_{provider_id.upper()}"
            base_url = os.getenv(f"{prefix}_BASE_URL", "").strip()
            api_key = os.getenv(f"{prefix}_API_KEY", "").strip()
            if base_url and api_key:
                result[provider_id] = {"base_url": base_url.rstrip("/"), "api_key": api_key}
        return result

    def list(self) -> list[CreationProviderInfo]:
        capabilities = {
            "higgsfield": ("video", "image", "audio"),
            "canva": ("design", "video", "image", "document"),
            "vercel": ("website", "deploy"),
            "render": ("website", "deploy"),
        }
        return [
            CreationProviderInfo(pid, capabilities.get(pid, ("creation",)), True)
            for pid in self.providers
        ]

    def dispatch(self, capability: str, payload: dict[str, Any], provider: str | None = None) -> CreationResult:
        if not isinstance(payload, dict):
            raise TypeError("creation payload must be an object")
        target = provider or self._select(capability)
        if target not in self.providers:
            raise RuntimeError(f"no configured creation provider for {capability}")
        config = self.providers[target]
        response = httpx.post(
            f"{config['base_url']}/v1/aethon/{capability}",
            headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"{target} returned HTTP {response.status_code}")
        data = response.json() if response.content else {}
        return CreationResult(target, capability, str(data.get("status", "submitted")), data)

    def _select(self, capability: str) -> str:
        preferred = {
            "video": ("higgsfield", "canva"),
            "image": ("higgsfield", "canva"),
            "design": ("canva",),
            "website": ("vercel", "render"),
            "deploy": ("vercel", "render"),
            "code": (),
        }.get(capability, tuple(self.providers))
        for candidate in preferred:
            if candidate in self.providers:
                return candidate
        if capability == "code":
            raise RuntimeError("code generation is handled by the AI provider fabric")
        raise RuntimeError(f"no configured provider supports {capability}")


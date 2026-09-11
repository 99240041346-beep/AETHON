from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from aethon.schemas import RiskClass


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    layer: str
    risk: RiskClass = RiskClass.LOW
    available: bool = False
    integration: str | None = None
    permission: str = 'owner'

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'layer': self.layer,
            'risk': self.risk.value,
            'available': self.available,
            'integration': self.integration,
            'permission': self.permission,
        }


class CapabilityRegistry:
    """Single discovery boundary for assistant, agent and operating-layer capabilities.

    A capability is advertised as available only when its backing integration is
    actually present. The registry deliberately reports unavailable capabilities
    instead of creating placeholder behavior.
    """

    def __init__(self, tool_names: set[str] | None = None) -> None:
        tools = tool_names or set()
        model_provider = os.getenv('AETHON_MODEL_PROVIDER', 'deterministic').lower()
        database = os.getenv('AETHON_DATABASE_URL', '')
        local_agent = os.getenv('AETHON_LOCAL_AGENT_URL', '')
        github = os.getenv('GITHUB_TOKEN', '')
        self._items = [
            Capability('CHAT', 'Unified conversational AI', 'assistant', available=True),
            Capability('WEB_SEARCH', 'Public web search', 'tool', available='web_search' in tools, integration='web_search'),
            Capability('WEB_FETCH', 'Secure public HTTP(S) page fetch', 'tool', available='web_fetch' in tools, integration='web_fetch'),
            Capability('CALCULATOR', 'Safe arithmetic calculation', 'tool', available='calculator' in tools, integration='calculator'),
            Capability('MODEL_PROVIDER', 'Configurable model provider', 'assistant', available=model_provider != 'deterministic', integration=model_provider),
            Capability('DATABASE', 'Durable PostgreSQL persistence', 'platform', available=database.startswith(('postgres://', 'postgresql://')), integration='postgresql'),
            Capability('GITHUB', 'Authorized GitHub repository workflows', 'agent', available=bool(github), integration='github'),
            Capability('LOCAL_COMPUTER', 'Authenticated local computer agent', 'operating', available=bool(local_agent), integration='local-agent'),
            Capability('ANDROID', 'Authorized Android device integration', 'operating', available=False, integration='android-bridge'),
            Capability('ADB', 'ADB-first local device bridge', 'operating', available=False, integration='local-agent-adb'),
            Capability('BROWSER', 'Interactive browser agent', 'agent', available=False, integration='browser-agent'),
            Capability('CODE_EXECUTION', 'Sandboxed generated-code execution', 'agent', available=False, integration='code-sandbox'),
            Capability('IMAGE_GENERATION', 'Image generation and editing', 'assistant', available=False, integration='image-provider'),
            Capability('DOCUMENT_GENERATION', 'Validated PDF/DOCX/XLSX/PPTX artifacts', 'assistant', available=False, integration='artifact-engine'),
            Capability('VOICE', 'Speech recognition and text-to-speech', 'assistant', available=False, integration='speech-provider'),
            Capability('AUTOMATION', 'Scheduled and recurring workflows', 'agent', available=False, integration='scheduler'),
            Capability('NOTIFICATIONS', 'Task and device notifications', 'assistant', available=False, integration='notification-provider'),
        ]

    def list(self) -> list[dict[str, Any]]:
        return [item.as_dict() for item in self._items]

    def get(self, name: str) -> dict[str, Any] | None:
        wanted = name.strip().upper()
        for item in self._items:
            if item.name == wanted:
                return item.as_dict()
        return None

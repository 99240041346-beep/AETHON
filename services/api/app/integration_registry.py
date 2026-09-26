from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IntegrationStatus:
    name: str
    category: str
    configured: bool
    mode: str
    required_env: tuple[str, ...]

    def as_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "configured": self.configured,
            "mode": self.mode,
            "required_env": list(self.required_env),
        }


class IntegrationRegistry:
    """Honest integration discovery: configured means credentials exist, never that an action succeeded."""

    _items = (
        ("github", "development", ("GITHUB_TOKEN",)),
        ("openai", "ai", ("AETHON_MODEL_API_KEY",)),
        ("postgresql", "storage", ("AETHON_DATABASE_URL",)),
        ("storage", "files", ("STORAGE_ENDPOINT", "STORAGE_ACCESS_KEY", "STORAGE_SECRET_KEY", "STORAGE_BUCKET")),
        ("gmail", "communication", ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET")),
        ("google-drive", "storage", ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")),
        ("calendar", "productivity", ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")),
        ("slack", "communication", ("SLACK_CLIENT_ID", "SLACK_CLIENT_SECRET")),
        ("discord", "communication", ("DISCORD_CLIENT_ID", "DISCORD_CLIENT_SECRET")),
        ("notion", "knowledge", ("NOTION_CLIENT_ID", "NOTION_CLIENT_SECRET")),
        ("dropbox", "storage", ("DROPBOX_CLIENT_ID", "DROPBOX_CLIENT_SECRET")),
    )

    def list(self) -> list[dict]:
        result = []
        for name, category, required in self._items:
            configured = all(bool(os.getenv(key, "").strip()) for key in required)
            result.append(IntegrationStatus(name, category, configured, "configured" if configured else "setup-required", required).as_dict())
        return result

    def get(self, name: str) -> dict | None:
        return next((item for item in self.list() if item["name"] == name.strip().lower()), None)

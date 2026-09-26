from __future__ import annotations

"""ASTRA safety-gated facade for existing AETHON web/device actions."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ActionRequest:
    action: str
    arguments: dict[str, Any]
    requires_confirmation: bool


class ActionPolicy:
    READ_ACTIONS = frozenset({"web_search", "web_fetch", "web_research", "SCREEN_READ", "DEVICE_INFO", "BATTERY_READ", "NETWORK_STATUS", "APP_LIST"})
    EXTERNAL_ACTIONS = frozenset({"OPEN_APP", "SCREEN_CLICK", "SCREEN_TEXT", "SCREEN_SCROLL", "SCREEN_BACK", "MEDIA_PLAY", "MEDIA_PAUSE", "MEDIA_STOP", "VOLUME_SET", "FLASHLIGHT_ON", "FLASHLIGHT_OFF", "SCREEN_INTERACT"})

    @classmethod
    def classify(cls, action: str, arguments: dict[str, Any] | None = None) -> ActionRequest:
        name = action.strip()
        if not name:
            raise ValueError("action is required")
        args = arguments if isinstance(arguments, dict) else {}
        if name in cls.READ_ACTIONS:
            return ActionRequest(name, args, False)
        if name in cls.EXTERNAL_ACTIONS:
            return ActionRequest(name, args, True)
        raise ValueError("action is not allowlisted")

    @staticmethod
    def validate_url(url: str) -> str:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("only absolute HTTP(S) URLs are allowed")
        if len(url) > 4000:
            raise ValueError("URL exceeds ASTRA bounds")
        return url.strip()

    @staticmethod
    def validate_device_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ValueError("device arguments must be an object")
        if len(arguments) > 20:
            raise ValueError("too many device arguments")
        return dict(arguments)

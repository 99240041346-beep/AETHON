from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class AssistantCommandIntent:
    action: str
    arguments: dict[str, Any]
    requires_confirmation: bool = False


class AssistantCommandBridge:
    """Bounded, deterministic command classifier; never executes device actions."""

    _OPEN_PATTERNS = (
        re.compile(r"^\s*(?:open|launch|start)\s+(.+?)\s*$", re.I),
        re.compile(r"^\s*(?:ఓపెన్|తెరువు|ప్రారంభించు)\s+(.+?)\s*$"),
    )

    _PACKAGES = {
        "youtube": "com.google.android.youtube",
        "యూట్యూబ్": "com.google.android.youtube",
        "chrome": "com.android.chrome",
        "క్రోమ్": "com.android.chrome",
        "settings": "com.android.settings",
        "సెట్టింగ్స్": "com.android.settings",
    }

    def classify(self, text: str, *, language: str = "te-IN") -> AssistantCommandIntent | None:
        if not text or not text.strip():
            return None
        for pattern in self._OPEN_PATTERNS:
            match = pattern.match(text)
            if not match:
                continue
            app = match.group(1).strip()
            package = self._PACKAGES.get(app.casefold()) or self._PACKAGES.get(app)
            if package is None:
                return None
            return AssistantCommandIntent(
                action="android.open_app",
                arguments={"app": app, "package": package},
                requires_confirmation=False,
            )
        return None

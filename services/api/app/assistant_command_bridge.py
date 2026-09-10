from __future__ import annotations
from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class CommandIntent:
    action: str
    arguments: dict[str, Any]
    requires_confirmation: bool = False
class AssistantCommandBridge:
    _APP_ALIASES = {"youtube":"com.google.android.youtube","యూట్యూబ్":"com.google.android.youtube","chrome":"com.android.chrome","క్రోమ్":"com.android.chrome","calculator":"com.google.android.calculator","క్యాలిక్యులేటర్":"com.google.android.calculator","settings":"com.android.settings","సెట్టింగ్స్":"com.android.settings"}
    def classify(self, text: str, *, language: str = "te-IN") -> CommandIntent | None:
        value=text.strip()
        if not value: return None
        lowered=value.lower()
        for prefix in ("open ","launch ","start ","ఓపెన్ ","తెరువు ","ప్రారంభించు "):
            if lowered.startswith(prefix.lower()):
                app=value[len(prefix):].strip().lower(); package=self._APP_ALIASES.get(app)
                if package: return CommandIntent("android.open_app", {"package":package,"app":app})
        return None
    @classmethod
    def allowed_packages(cls)->dict[str,str]: return dict(cls._APP_ALIASES)

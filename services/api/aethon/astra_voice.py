from __future__ import annotations

"""ASTRA voice-session contract over the existing bounded AETHON voice agent."""

from dataclasses import dataclass
from typing import Any
from app.voice_agent import BoundedVoiceAgent, VoiceRequest, VoiceResult

@dataclass(frozen=True)
class ASTRASession:
    session_id: str
    locale: str
    wake_enabled: bool = False
    speak_responses: bool = True

class ASTRAVoice:
    def __init__(self, agent: BoundedVoiceAgent | None = None):
        self.agent = agent or BoundedVoiceAgent()

    def session(self, session_id: str, locale: str = "auto", *, wake_enabled: bool = False) -> ASTRASession:
        if not session_id.strip():
            raise ValueError("session_id is required")
        if not locale.strip():
            raise ValueError("locale is required")
        return ASTRASession(session_id.strip(), locale.strip(), wake_enabled=wake_enabled)

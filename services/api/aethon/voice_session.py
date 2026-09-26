from __future__ import annotations

"""Provider-neutral conversational voice session for ASTRA."""

from dataclasses import dataclass, field
from time import monotonic


@dataclass
class VoiceTurn:
    user_text: str
    assistant_text: str
    language: str


@dataclass
class VoiceSession:
    session_id: str
    language: str = "auto"
    active: bool = True
    interrupted: bool = False
    started_at: float = field(default_factory=monotonic)
    turns: list[VoiceTurn] = field(default_factory=list)

    MAX_TURNS = 100

    def add_turn(self, user_text: str, assistant_text: str, language: str | None = None) -> None:
        if not user_text.strip() or not assistant_text.strip():
            raise ValueError("voice turn text is required")
        self.language = language or self.language
        self.turns.append(VoiceTurn(user_text, assistant_text, self.language))
        if len(self.turns) > self.MAX_TURNS:
            del self.turns[:-self.MAX_TURNS]

    def interrupt(self) -> None:
        self.interrupted = True

    def resume(self) -> None:
        self.interrupted = False
        self.active = True

    def stop(self) -> None:
        self.active = False
        self.interrupted = False

    def context(self, max_turns: int = 12) -> tuple[VoiceTurn, ...]:
        if not 1 <= max_turns <= self.MAX_TURNS:
            raise ValueError("invalid voice context bound")
        return tuple(self.turns[-max_turns:])


class VoiceSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}

    def create(self, session_id: str, language: str = "auto") -> VoiceSession:
        if not session_id.strip():
            raise ValueError("session_id is required")
        session = VoiceSession(session_id, language)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> VoiceSession:
        if session_id not in self._sessions:
            raise KeyError("unknown voice session")
        return self._sessions[session_id]


__all__ = ["VoiceTurn", "VoiceSession", "VoiceSessionManager"]

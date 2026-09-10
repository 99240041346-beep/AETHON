from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any


class AssistantMode(str, Enum):
    CHAT = "CHAT"
    TASK = "TASK"
    ACTION = "ACTION"


@dataclass(frozen=True)
class AssistantIntent:
    mode: AssistantMode
    text: str
    action: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False


@dataclass(frozen=True)
class AssistantReply:
    text: str
    intent: AssistantIntent
    spoken: bool = True


class AssistantOrchestrator:
    """Bounded front door for AETHON's unified assistant experience."""

    _OPEN_APP = re.compile(r"(?:open|launch|start)\s+([a-zA-Z0-9._ -]{2,64})$", re.I)
    _OPEN_APP_TE = re.compile(r"(?:ఓపెన్|తెరువు|ప్రారంభించు)\s+([\w ._-]{2,64})$", re.I)

    def classify(self, text: str) -> AssistantIntent:
        value = text.strip()
        lowered = value.lower()
        if not value:
            raise ValueError("assistant input cannot be empty")
        match = self._OPEN_APP.search(value) or self._OPEN_APP_TE.search(value)
        if match:
            return AssistantIntent(AssistantMode.ACTION, value, "android.open_app", {"app": match.group(1).strip()})
        action_words = ("open ", "launch ", "start ", "send ", "call ", "message ", "play ", "stop ", "turn on", "turn off", "ఓపెన్", "తెరువు", "కాల్", "మెసేజ్", "ప్లే", "ఆపు", "ఆన్ చేయి", "ఆఫ్ చేయి")
        if any(lowered.startswith(word.lower()) for word in action_words):
            return AssistantIntent(AssistantMode.ACTION, value, "assistant.action.request", {"command": value}, True)
        task_words = ("do ", "make ", "create ", "find ", "research ", "analyze ", "చేయి", "కనుగొను", "విశ్లేషించు")
        if any(lowered.startswith(word.lower()) for word in task_words):
            return AssistantIntent(AssistantMode.TASK, value, "agent.task", {"goal": value})
        return AssistantIntent(AssistantMode.CHAT, value)

    def respond(self, text: str, *, language: str = "te-IN") -> AssistantReply:
        intent = self.classify(text)
        telugu = language.lower().startswith("te")
        if intent.mode is AssistantMode.ACTION and intent.requires_confirmation:
            message = "Harsha, ఈ action చేయడానికి మీ confirmation అవసరం. కొనసాగించనా?" if telugu else "Harsha, I need your confirmation before performing that action. Continue?"
        elif intent.mode is AssistantMode.ACTION:
            message = "సరే Harsha, నేను ఆ action కోసం plan చేస్తున్నాను." if telugu else "Okay Harsha, I’m planning that action."
        elif intent.mode is AssistantMode.TASK:
            message = "సరే Harsha, నేను task ని plan చేసి verify చేస్తాను." if telugu else "Okay Harsha, I’ll plan the task and verify the result."
        else:
            message = "చెప్పు Harsha, నేను వింటున్నాను." if telugu else "Tell me, Harsha. I’m listening."
        return AssistantReply(text=message, intent=intent)

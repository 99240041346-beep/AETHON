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
    _CLICK = re.compile(r"(?:click|tap|press)\s+(.+)$", re.I)
    _CLICK_TE = re.compile(r"(?:క్లిక్|ట్యాప్|నొక్కు)\s+(.+)$", re.I)
    _SCROLL = re.compile(r"(?:scroll|swipe)\s+(up|down|forward|backward)$", re.I)
    _TEXT = re.compile(r"(?:type|enter|write)\s+(.+?)\s+(?:in|into)\s+(.+)$", re.I)
    _BACK = re.compile(r"(?:go\s+back|press\s+back|back)$", re.I)

    def classify(self, text: str) -> AssistantIntent:
        value = text.strip()
        lowered = value.lower()
        if not value:
            raise ValueError("assistant input cannot be empty")

        match = self._OPEN_APP.search(value) or self._OPEN_APP_TE.search(value)
        if match:
            return AssistantIntent(AssistantMode.ACTION, value, "android.open_app", {"app": match.group(1).strip()})

        match = self._CLICK.search(value) or self._CLICK_TE.search(value)
        if match:
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_click", {"text": match.group(1).strip()}, True)

        match = self._SCROLL.search(value)
        if match:
            direction = match.group(1).lower()
            if direction == "up": direction = "backward"
            if direction == "down": direction = "forward"
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_scroll", {"direction": direction}, True)

        match = self._TEXT.search(value)
        if match:
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_text", {"value": match.group(1), "text": match.group(2).strip()}, True)

        if self._BACK.search(value):
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_back", {}, True)

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

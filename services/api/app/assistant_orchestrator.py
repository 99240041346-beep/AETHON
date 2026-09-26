from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any

from aethon.intent_analyzer import IntentAnalyzer, IntentType


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
    intent_type: IntentType = IntentType.NORMAL_CHAT


@dataclass(frozen=True)
class AssistantReply:
    text: str
    intent: AssistantIntent
    spoken: bool = True


class AssistantOrchestrator:
    """Bounded front door backed by a typed, explainable intent analyzer."""

    _OPEN_APP = re.compile(r"(?:open|launch|start)\s+([a-zA-Z0-9._ -]{2,64})$", re.I)
    _OPEN_APP_TE = re.compile(r"(?:ఓపెన్|తెరువు|ప్రారంభించు)\s+([\w ._-]{2,64})$", re.I)
    _CLICK = re.compile(r"(?:click|tap|press)\s+(.+)$", re.I)
    _CLICK_TE = re.compile(r"(?:క్లిక్|ట్యాప్|నొక్కు)\s+(.+)$", re.I)
    _SCROLL = re.compile(r"(?:scroll|swipe)\s+(up|down|forward|backward)$", re.I)
    _TEXT = re.compile(r"(?:type|enter|write)\s+(.+?)\s+(?:in|into)\s+(.+)$", re.I)
    _BACK = re.compile(r"(?:go\s+back|press\s+back|back)$", re.I)
    _PACKAGES = {"youtube": "com.google.android.youtube", "chrome": "com.android.chrome", "settings": "com.android.settings"}

    def __init__(self, analyzer: IntentAnalyzer | None = None) -> None:
        self.analyzer = analyzer or IntentAnalyzer()

    def classify(self, text: str, *, context: str | None = None) -> AssistantIntent:
        value = text.strip()
        lowered = value.lower()
        if not value:
            raise ValueError("assistant input cannot be empty")

        match = self._OPEN_APP.search(value) or self._OPEN_APP_TE.search(value)
        if match:
            app = match.group(1).strip()
            package = self._PACKAGES.get(app.casefold())
            if package:
                return AssistantIntent(AssistantMode.ACTION, value, "android.open_app", {"app": app, "package": package}, False, IntentType.DEVICE_ACTION)

        match = self._CLICK.search(value) or self._CLICK_TE.search(value)
        if match:
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_click", {"text": match.group(1).strip()}, True, IntentType.DEVICE_ACTION)

        match = self._SCROLL.search(value)
        if match:
            direction = match.group(1).lower()
            direction = {"up": "backward", "down": "forward"}.get(direction, direction)
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_scroll", {"direction": direction}, True, IntentType.DEVICE_ACTION)

        match = self._TEXT.search(value)
        if match:
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_text", {"value": match.group(1), "text": match.group(2).strip()}, True, IntentType.DEVICE_ACTION)

        if self._BACK.search(value):
            return AssistantIntent(AssistantMode.ACTION, value, "android.screen_back", {}, True, IntentType.DEVICE_ACTION)

        analysis = self.analyzer.analyze(value, context=context)
        if analysis.intent is IntentType.NORMAL_CHAT:
            return AssistantIntent(AssistantMode.CHAT, value, arguments=analysis.arguments or {}, intent_type=analysis.intent)

        if analysis.intent in {IntentType.DEVICE_ACTION, IntentType.EXTERNAL_ACTION}:
            return AssistantIntent(
                AssistantMode.ACTION, value, "assistant.action.request",
                analysis.arguments or {"command": value},
                analysis.requires_confirmation,
                analysis.intent,
            )

        return AssistantIntent(
            AssistantMode.TASK,
            value,
            "agent.task",
            {"goal": value, "intent": analysis.intent.value, **(analysis.arguments or {})},
            analysis.requires_confirmation,
            analysis.intent,
        )

    def respond(self, text: str, *, language: str = "te-IN", context: str | None = None) -> AssistantReply:
        intent = self.classify(text, context=context)
        telugu = language.lower().startswith("te")
        if intent.mode is AssistantMode.ACTION and intent.requires_confirmation:
            message = "ఈ action చేయడానికి మీ confirmation అవసరం. కొనసాగించనా?" if telugu else "I need your confirmation before performing that action. Continue?"
        elif intent.mode is AssistantMode.ACTION:
            message = "సరే, నేను ఆ action కోసం plan చేస్తున్నాను." if telugu else "Okay, I’m planning that action."
        elif intent.mode is AssistantMode.TASK:
            message = "సరే, నేను task ని plan చేసి verify చేస్తాను." if telugu else "Okay, I’ll plan the task and verify the result."
        else:
            message = "చెప్పు, నేను వింటున్నాను." if telugu else "Tell me. I’m listening."
        return AssistantReply(text=message, intent=intent)

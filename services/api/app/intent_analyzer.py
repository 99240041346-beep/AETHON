from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

class IntentType(str, Enum):
    NORMAL_CHAT = "NORMAL_CHAT"
    RESEARCH = "RESEARCH"
    SEARCH = "SEARCH"
    FILE_ANALYSIS = "FILE_ANALYSIS"
    VISION = "VISION"
    VOICE = "VOICE"
    CODING = "CODING"
    DATA_ANALYSIS = "DATA_ANALYSIS"
    DOCUMENT_GENERATION = "DOCUMENT_GENERATION"
    IMAGE_GENERATION = "IMAGE_GENERATION"
    AGENT_TASK = "AGENT_TASK"
    AUTOMATION = "AUTOMATION"
    MEMORY = "MEMORY"
    PROJECT = "PROJECT"
    TASK = "TASK"
    EXTERNAL_ACTION = "EXTERNAL_ACTION"
    DEVICE_ACTION = "DEVICE_ACTION"

@dataclass(frozen=True)
class IntentAnalysis:
    intent: IntentType
    confidence: float
    signals: tuple[str, ...]
    requires_confirmation: bool = False
    arguments: dict[str, object] | None = None

class IntentAnalyzer:
    """Bounded, explainable intent analysis; it never grants tool permission."""
    _MEMORY = re.compile(r"(?:remember|save this|store this|what do you remember|forget|delete that memory|don't remember)", re.I)
    _DEVICE = re.compile(r"(?:open|launch|start)\s+(?:youtube|chrome|settings|app)|(?:tap|click|press|scroll|swipe)\b|screen|flashlight|volume|battery", re.I)
    _EXTERNAL = re.compile(r"(?:send|email|message|call|post|submit|purchase|buy|delete|invite|push)\b", re.I)
    _IMAGE = re.compile(r"(?:generate|create|make|draw|design)\s+(?:an?\s+)?(?:image|picture|poster|logo|illustration)", re.I)
    _VISION = re.compile(r"(?:look at|analyze|describe|read|ocr|what is in)\s+(?:this|the)\s+(?:image|photo|screenshot|diagram)", re.I)
    _DATA = re.compile(r"(?:csv|xlsx?|dataset|dataframe|column|row|correlation|outlier|statistics|chart|plot|graph)", re.I)
    _FILE = re.compile(r"(?:pdf|docx?|xlsx?|csv|json|txt|md|zip|file|attachment)", re.I)
    _CODE = re.compile(r"(?:traceback|stack trace|compile|debug|bug|exception|function|class\s+\w+|api endpoint|sql)", re.I)
    _DOCUMENT = re.compile(r"(?:write|draft|generate|create)\s+(?:an?\s+)?(?:email|essay|report|resume|cover letter|article|story|speech|proposal|documentation)", re.I)
    _PROJECT = re.compile(r"(?:create|start|set up)\s+(?:a\s+)?project|for (?:this|the) project", re.I)
    _TASK = re.compile(r"(?:create|add|break.*into|complete|finish|overdue)\s+(?:a\s+)?task|todo|to-do", re.I)
    _AUTOMATION = re.compile(r"(?:automate|automation|schedule|recurring|every day|every week|webhook|when .* then)", re.I)
    _AGENT = re.compile(r"(?:run|use|start)\s+(?:an?\s+)?(?:agent|coding agent|research agent|data agent)|autonomously|multi-step", re.I)
    _RESEARCH = re.compile(r"(?:research|compare|comparison|latest|current|sources?|evidence|eligib|price|policy|how does|what is)", re.I)
    _SEARCH = re.compile(r"(?:search|find online|look up|google)\b", re.I)
    _VOICE = re.compile(r"(?:voice|speak|say aloud|transcribe|speech to text|text to speech)", re.I)

    def analyze(self, text: str, *, context: str | None = None) -> IntentAnalysis:
        value = text.strip()
        if not value: raise ValueError("assistant input cannot be empty")
        if self._MEMORY.search(value): return IntentAnalysis(IntentType.MEMORY, 0.99, ("memory-language",))
        if self._DEVICE.search(value): return IntentAnalysis(IntentType.DEVICE_ACTION, 0.96, ("device-language",), True)
        if self._EXTERNAL.search(value): return IntentAnalysis(IntentType.EXTERNAL_ACTION, 0.94, ("external-side-effect-language",), True)
        if self._IMAGE.search(value): return IntentAnalysis(IntentType.IMAGE_GENERATION, 0.93, ("image-generation-structure",))
        if self._VISION.search(value): return IntentAnalysis(IntentType.VISION, 0.92, ("vision-language",))
        if self._DATA.search(value): return IntentAnalysis(IntentType.DATA_ANALYSIS, 0.93, ("data-structure",))
        if self._FILE.search(value) and re.search(r"\b(analy[sz]|extract|read|parse|summar)", value, re.I): return IntentAnalysis(IntentType.FILE_ANALYSIS, 0.92, ("file-analysis-structure",))
        if self._CODE.search(value): return IntentAnalysis(IntentType.CODING, 0.91, ("code-language",))
        if self._DOCUMENT.search(value): return IntentAnalysis(IntentType.DOCUMENT_GENERATION, 0.90, ("document-form",))
        if self._PROJECT.search(value): return IntentAnalysis(IntentType.PROJECT, 0.90, ("project-language",))
        if self._TASK.search(value): return IntentAnalysis(IntentType.TASK, 0.90, ("task-language",))
        if self._AUTOMATION.search(value): return IntentAnalysis(IntentType.AUTOMATION, 0.90, ("automation-language",))
        if self._AGENT.search(value): return IntentAnalysis(IntentType.AGENT_TASK, 0.89, ("agent-language",))
        if context and re.search(r"\\b(?:same|that|this|previous|above|it|them|more)\\b", value, re.I):\n            return IntentAnalysis(IntentType.NORMAL_CHAT, 0.70, ("contextual-reference",), arguments={"needs_context": True})\n        if self._RESEARCH.search(value):
            signal = "freshness-request" if re.search(r"\b(latest|current)\b", value, re.I) else "research-question-structure"
            return IntentAnalysis(IntentType.RESEARCH, 0.95 if signal == "freshness-request" else 0.88, (signal,))
        if self._SEARCH.search(value) or re.search(r"https?://\S+", value): return IntentAnalysis(IntentType.SEARCH, 0.87, ("search-language",))
        if self._VOICE.search(value): return IntentAnalysis(IntentType.VOICE, 0.86, ("voice-language",))
        if context and re.search(r"\b(?:same|that|this|previous|above|it|them|more)\b", value, re.I): return IntentAnalysis(IntentType.NORMAL_CHAT, 0.70, ("contextual-reference",), arguments={"needs_context": True})
        return IntentAnalysis(IntentType.NORMAL_CHAT, 0.60, ("default-safe-chat",))
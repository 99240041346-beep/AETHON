from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

@dataclass
class ContextState:
    conversation: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    research: list[dict[str, Any]] = field(default_factory=list)
    project: dict[str, Any] | None = None
    file: dict[str, Any] | None = None
    task: dict[str, Any] | None = None
    agent_run: dict[str, Any] | None = None

class ContextManager:
    def __init__(self, max_messages: int = 40, max_results: int = 20) -> None:
        self.max_messages = max(1, max_messages)
        self.max_results = max(1, max_results)

    def add_message(self, state: ContextState, message: dict[str, Any]) -> None:
        state.conversation.append(message)
        del state.conversation[:-self.max_messages]

    def add_tool_result(self, state: ContextState, result: dict[str, Any]) -> None:
        state.tool_results.append(result)
        del state.tool_results[:-self.max_results]

    def resolve_reference(self, text: str, state: ContextState) -> dict[str, Any]:
        lowered = text.casefold()
        if any(token in lowered for token in ("this file", "the file")) and state.file:
            return {"type": "file", "value": state.file}
        if any(token in lowered for token in ("this project", "the project")) and state.project:
            return {"type": "project", "value": state.project}
        if any(token in lowered for token in ("this task", "the task")) and state.task:
            return {"type": "task", "value": state.task}
        if any(token in lowered for token in ("that result", "previous result", "the result")) and state.tool_results:
            return {"type": "tool_result", "value": state.tool_results[-1]}
        if state.conversation:
            return {"type": "conversation", "value": state.conversation[-1]}
        return {"type": "unresolved", "value": None}

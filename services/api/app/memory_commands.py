from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from aethon.memory_engine import MemorySecurityError, redact_secrets
from aethon.memory_repository import MemoryRepository


@dataclass(frozen=True)
class MemoryCommand:
    action: str
    content: str = ""
    query: str = ""


class NaturalMemory:
    """Small deterministic command parser; storage remains owner-scoped and secret-redacting."""

    _REMEMBER = re.compile(r"^(?:remember|save to memory|save this|store this)\s*[:,-]?\s*(.+)$", re.I | re.S)
    _FORGET = re.compile(r"^(?:forget|delete from memory|remove from memory)\s*[:,-]?\s*(.+)$", re.I | re.S)
    _SEARCH = re.compile(r"^(?:what do you remember about|what do you know about|recall)\s+(.+)$", re.I | re.S)
    _CLEAR = re.compile(r"^(?:forget everything|clear my memory|clear all memory)$", re.I)

    def __init__(self, repository: MemoryRepository | None = None):
        self.repository = repository or MemoryRepository()

    def parse(self, text: str) -> MemoryCommand | None:
        value = " ".join(text.strip().split())
        if not value:
            return None
        if self._CLEAR.match(value):
            return MemoryCommand("clear")
        match = self._REMEMBER.match(value)
        if match:
            return MemoryCommand("remember", content=match.group(1).strip())
        match = self._FORGET.match(value)
        if match:
            return MemoryCommand("forget", content=match.group(1).strip())
        match = self._SEARCH.match(value)
        if match:
            return MemoryCommand("search", query=match.group(1).strip())
        return None

    def execute(self, command: MemoryCommand, *, owner_id: str, project_id: str | None = None) -> dict[str, Any]:
        namespace = "project" if project_id else "default"
        if command.action == "remember":
            content = redact_secrets(command.content).strip()
            if not content or content == "[REDACTED]":
                raise MemorySecurityError("memory content contains only protected secret material")
            memory_id = "nl:" + str(abs(hash((owner_id, project_id, content.casefold()))))
            record = self.repository.put(
                memory_id, content, owner_id=owner_id, project_id=project_id,
                namespace=namespace, memory_type="semantic", source="user_natural_language",
                confidence=0.95,
            )
            return {"action": "remembered", "memory": record.__dict__}
        if command.action == "search":
            records = self.repository.search(command.query, owner_id=owner_id, project_id=project_id, namespace=namespace, limit=10)
            return {"action": "found", "memories": [record.__dict__ for record in records]}
        if command.action == "forget":
            records = self.repository.search(command.content, owner_id=owner_id, project_id=project_id, namespace=namespace, limit=20)
            deleted = []
            for record in records:
                if command.content.casefold() in record.content.casefold():
                    if self.repository.delete(record.memory_id, owner_id=owner_id, project_id=project_id, namespace=namespace):
                        deleted.append(record.memory_id)
            return {"action": "forgotten", "count": len(deleted), "memory_ids": deleted}
        if command.action == "clear":
            # The public memory API intentionally has no destructive bulk-delete endpoint.
            # Return a safe maintenance instruction rather than silently deleting everything.
            return {"action": "clear_requires_confirmation", "message": "Clearing all memory requires explicit confirmation and a scoped maintenance operation."}
        raise MemorySecurityError("unsupported memory command")

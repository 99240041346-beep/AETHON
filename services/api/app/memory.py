from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class MemoryItem:
    key: str
    value: Any
    project_id: str | None = None


class MemoryStore(Protocol):
    def put(self, key: str, value: Any, project_id: str | None = None) -> None: ...
    def search(self, query: str, project_id: str | None = None, limit: int = 10) -> list[MemoryItem]: ...


class InMemoryStore:
    """AETHON-0 memory abstraction; replaceable by PostgreSQL/pgvector later."""

    def __init__(self) -> None:
        self._items: list[MemoryItem] = []

    def put(self, key: str, value: Any, project_id: str | None = None) -> None:
        self._items = [
            item for item in self._items
            if not (item.key == key and item.project_id == project_id)
        ]
        self._items.append(MemoryItem(key=key, value=value, project_id=project_id))

    def search(self, query: str, project_id: str | None = None, limit: int = 10) -> list[MemoryItem]:
        q = query.lower().strip()
        matches = []
        for item in reversed(self._items):
            if item.project_id not in (None, project_id) and project_id is not None:
                continue
            haystack = f"{item.key} {item.value}".lower()
            if not q or q in haystack:
                matches.append(item)
            if len(matches) >= limit:
                break
        return matches

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DecisionContext:
    """Bounded, data-only context supplied to agent planning/reasoning."""

    memories: tuple[str, ...] = ()


class DecisionContextBuilder:
    """Convert scoped memory records into deterministic planning context."""

    def __init__(self, *, max_items: int = 5, max_chars: int = 4000) -> None:
        if not 1 <= max_items <= 20:
            raise ValueError("max_items must be between 1 and 20")
        if not 100 <= max_chars <= 20000:
            raise ValueError("max_chars must be between 100 and 20000")
        self.max_items = max_items
        self.max_chars = max_chars

    def build(self, items: Iterable[object]) -> DecisionContext:
        result: list[str] = []
        seen: set[str] = set()
        for item in items:
            text = str(getattr(item, "content", item)).strip()
            if not text:
                continue
            text = text[: self.max_chars]
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(text)
            if len(result) >= self.max_items:
                break
        return DecisionContext(tuple(result))

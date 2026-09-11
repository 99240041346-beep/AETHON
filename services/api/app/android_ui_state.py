from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MAX_UI_NODES = 250
MAX_TEXT = 300


@dataclass(frozen=True)
class UiElement:
    index: int
    class_name: str
    package_name: str
    text: str
    description: str
    clickable: bool
    scrollable: bool
    editable: bool
    enabled: bool

    @property
    def label(self) -> str:
        return self.text or self.description

    @property
    def role(self) -> str:
        cls = self.class_name.casefold()
        if "edittext" in cls or self.editable:
            return "text_field"
        if "button" in cls or self.clickable:
            return "button"
        if "checkbox" in cls:
            return "checkbox"
        if "switch" in cls:
            return "switch"
        if "scroll" in cls or self.scrollable:
            return "scroll_container"
        if "textview" in cls:
            return "text"
        return "unknown"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)[:MAX_TEXT]


def normalize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Convert a bounded SCREEN_READ payload into stable semantic UI state."""
    if not isinstance(snapshot, dict):
        raise ValueError("UI snapshot must be an object")
    if snapshot.get("connected") is False:
        return {"connected": False, "node_count": 0, "elements": []}

    raw_nodes = snapshot.get("nodes", [])
    if not isinstance(raw_nodes, list):
        raise ValueError("UI snapshot nodes must be a list")

    elements: list[dict[str, Any]] = []
    for raw in raw_nodes[:MAX_UI_NODES]:
        if not isinstance(raw, dict):
            continue
        element = UiElement(
            index=int(raw.get("index", len(elements))),
            class_name=_text(raw.get("class")),
            package_name=_text(raw.get("package")),
            text=_text(raw.get("text")),
            description=_text(raw.get("description")),
            clickable=bool(raw.get("clickable", False)),
            scrollable=bool(raw.get("scrollable", False)),
            editable=bool(raw.get("editable", False)),
            enabled=bool(raw.get("enabled", False)),
        )
        elements.append({
            "index": element.index,
            "role": element.role,
            "label": element.label,
            "text": element.text,
            "description": element.description,
            "class": element.class_name,
            "package": element.package_name,
            "clickable": element.clickable,
            "scrollable": element.scrollable,
            "editable": element.editable,
            "enabled": element.enabled,
        })

    return {
        "connected": bool(snapshot.get("connected", True)),
        "node_count": min(int(snapshot.get("node_count", len(elements))), MAX_UI_NODES),
        "elements": elements,
    }


def find_candidates(state: dict[str, Any], label: str) -> list[dict[str, Any]]:
    """Return enabled semantic matches without inventing coordinates or actions."""
    needle = label.strip().casefold()
    if not needle:
        return []
    candidates = []
    for element in state.get("elements", []):
        if not isinstance(element, dict) or not element.get("enabled", False):
            continue
        values = (element.get("text", ""), element.get("description", ""), element.get("label", ""))
        if any(needle == str(value).casefold() for value in values if value):
            candidates.append(element)
    return candidates

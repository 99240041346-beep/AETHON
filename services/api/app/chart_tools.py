from __future__ import annotations

import re
from typing import Any


def _chart_type(text: str) -> str | None:
    lowered = text.casefold()
    for word, kind in (("scatter", "scatter"), ("pie", "pie"), ("line", "line"), ("bar", "bar")):
        if word in lowered and any(token in lowered for token in ("chart", "plot", "graph")):
            return kind
    return "bar" if any(token in lowered for token in ("graph", "plot")) else None


def _payload(text: str) -> str:
    lowered = text.casefold()
    for marker in ("data:", "values:"):
        position = lowered.find(marker)
        if position >= 0:
            return text[position + len(marker):].strip()
    for marker in (" of ", " for ", " showing "):
        position = lowered.find(marker)
        if position >= 0:
            tail = text[position + len(marker):]
            if re.search(r"[=:]|-?\d+(?:\.\d+)?", tail):
                return tail.strip(" .")
    return text


def _title(text: str, kind: str) -> str:
    cleaned = re.sub(r"(?i)\b(create|make|draw|show|generate|plot|graph|a|an|the)\b", " ", text)
    cleaned = re.sub(r"(?i)\b(bar|line|pie|scatter)\s+(?:chart|plot|graph)\b", " ", cleaned)
    cleaned = re.sub(r"(?i)\b(data|values)\s*:", " ", cleaned)
    cleaned = re.sub(r"[:;,]+.*$", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    return cleaned[:80].title() if cleaned else f"{kind.title()} chart"


def _pairs(payload: str) -> list[tuple[str, float]]:
    pairs = []
    for chunk in re.split(r"[,;\n]+", payload):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = re.match(r"""^\s*["']?(.+?)["']?\s*(?:=|:)\s*(-?\d+(?:\.\d+)?)\s*$""", chunk)
        if not match:
            match = re.match(r"""^\s*([A-Za-z][A-Za-z0-9 _-]{0,50})\s+(-?\d+(?:\.\d+)?)\s*$""", chunk)
        if match:
            pairs.append((match.group(1).strip(" \"'"), float(match.group(2))))
    return pairs[:30]


def _scatter(payload: str) -> list[dict[str, float]]:
    points = []
    for chunk in re.split(r"[;\n]+", payload):
        nums = re.findall(r"-?\d+(?:\.\d+)?", chunk)
        if len(nums) >= 2:
            points.append({"x": float(nums[0]), "y": float(nums[1])})
    return points[:50]


def build_chart(text: str) -> dict[str, Any] | None:
    kind = _chart_type(text)
    if kind is None:
        return None
    payload = _payload(text)
    title = _title(text, kind)
    if kind == "scatter":
        data = _scatter(payload)
        if len(data) < 2:
            return None
        return {"chartType": "scatter", "meta": {"title": title, "description": "Chart generated from supplied numeric pairs."},
                "xKey": "x", "xAxisLabel": "X", "series": [{"dataKey": "y", "label": "Y"}], "data": data}
    pairs = _pairs(payload)
    if len(pairs) < 2:
        return None
    if kind == "pie":
        return {"chartType": "pie", "meta": {"title": title, "description": "Part-to-whole chart generated from supplied values."},
                "nameKey": "category", "valueKey": "value", "series": [{"dataKey": "value", "label": "Value"}],
                "data": [{"category": k, "value": v} for k, v in pairs]}
    return {"chartType": kind, "meta": {"title": title, "description": "Chart generated from supplied values."},
            "xKey": "category", "series": [{"dataKey": "value", "label": "Value"}],
            "data": [{"category": k, "value": v} for k, v in pairs]}


class ChartTool:
    def __init__(self) -> None:
        self.spec = {
            "name": "chart",
            "description": "Create a bar, line, pie, or scatter visualization from user-supplied data.",
            "input_schema": {"type": "object", "properties": {"text": {"type": "string", "maxLength": 8000}},
                             "required": ["text"], "additionalProperties": False},
            "output_schema": {"type": "object"}, "risk": "LOW", "side_effects": False,
            "timeout_seconds": 5, "max_retries": 0, "authentication": "owner", "audit_required": True,
        }

    def execute(self, text: str) -> dict[str, Any]:
        chart = build_chart(text)
        if chart is None:
            raise ValueError("I need a chart type and at least two data points. Example: bar chart: Apples=30, Oranges=20.")
        return chart

from __future__ import annotations

"""ASTRA creation contracts built on deterministic AETHON primitives."""

from dataclasses import dataclass
from typing import Any

from app.chart_tools import ChartTool


@dataclass(frozen=True)
class CreationResult:
    kind: str
    content: Any
    metadata: dict[str, Any]


class CreationService:
    """Safe creation facade; side-effectful exporters can plug into this contract."""

    def __init__(self, chart: ChartTool | None = None):
        self.chart = chart or ChartTool()

    def chart_from_text(self, text: str) -> CreationResult:
        result = self.chart.execute(text)
        return CreationResult("chart", result, {"deterministic": True})

    def markdown_document(self, title: str, body: str) -> CreationResult:
        title = title.strip()
        body = body.strip()
        if not title or not body:
            raise ValueError("title and body are required")
        if len(title) > 200 or len(body) > 100_000:
            raise ValueError("document exceeds ASTRA bounds")
        return CreationResult("markdown", f"# {title}\n\n{body}\n", {"format": "markdown"})

    def code_artifact(self, language: str, source: str) -> CreationResult:
        language = language.strip().lower()
        source = source.strip()
        allowed = {"python", "javascript", "typescript", "java", "kotlin", "sql", "bash"}
        if language not in allowed:
            raise ValueError("unsupported language")
        if not source:
            raise ValueError("source is required")
        if len(source) > 100_000:
            raise ValueError("code artifact exceeds ASTRA bounds")
        return CreationResult("code", source, {"language": language, "execution": "not_requested"})


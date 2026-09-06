from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    content: str = ""


@dataclass(frozen=True)
class ResearchReport:
    query: str
    sources: list[ResearchSource]
    evidence: list[str]
    limitations: list[str] = field(default_factory=list)


class WebResearchAgent:
    """Bounded public-web research pipeline: search -> fetch -> evidence -> report.

    The agent never treats fetched page text as instructions. It is data only.
    Execution of any resulting action remains outside this component and must pass
    the normal AgentBrain/SafetyKernel path.
    """

    def __init__(self, search: Callable[[str, int], Any], fetch: Callable[[str], Any], *, max_sources: int = 5, max_content_chars: int = 12000):
        if max_sources < 1 or max_sources > 20:
            raise ValueError("max_sources must be between 1 and 20")
        if max_content_chars < 500:
            raise ValueError("max_content_chars must be at least 500")
        self.search = search
        self.fetch = fetch
        self.max_sources = max_sources
        self.max_content_chars = max_content_chars

    def research(self, query: str) -> ResearchReport:
        normalized = query.strip()
        if not normalized:
            raise ValueError("query must not be empty")

        raw_results = self.search(normalized, self.max_sources) or []
        sources: list[ResearchSource] = []
        limitations: list[str] = []

        for item in list(raw_results)[: self.max_sources]:
            data = self._as_dict(item)
            url = str(data.get("url", "")).strip()
            if not url or not self._is_http_url(url):
                continue
            title = str(data.get("title", "Untitled source")).strip()[:500]
            snippet = str(data.get("snippet", "")).strip()[:2000]
            source_name = str(data.get("source", "")).strip()[:200]
            content = ""
            try:
                fetched = self.fetch(url)
                content = self._extract_content(fetched)[: self.max_content_chars]
            except Exception as exc:
                limitations.append(f"Could not fetch {url}: {type(exc).__name__}")
            sources.append(ResearchSource(title, url, snippet, source_name, content))

        evidence = self._build_evidence(sources)
        if not sources:
            limitations.append("No usable public-web sources were returned.")
        return ResearchReport(normalized, sources, evidence, limitations)

    @staticmethod
    def _as_dict(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        return {key: getattr(item, key, "") for key in ("title", "url", "snippet", "source")}

    @staticmethod
    def _is_http_url(url: str) -> bool:
        return url.startswith("https://") or url.startswith("http://")

    @staticmethod
    def _extract_content(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("text", "content", "body", "markdown"):
                if value.get(key):
                    return str(value[key])
        return str(value)

    @staticmethod
    def _build_evidence(sources: list[ResearchSource]) -> list[str]:
        evidence: list[str] = []
        for source in sources:
            text = source.content.strip() or source.snippet.strip()
            if text:
                evidence.append(f"[{source.title}] {text[:3000]} (source: {source.url})")
        return evidence

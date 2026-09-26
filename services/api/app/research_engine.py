from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.web_research import ResearchReport, WebResearchAgent


@dataclass(frozen=True)
class ResearchResult:
    report: ResearchReport
    verified_sources: int
    source_domains: tuple[str, ...]


class ResearchEngine:
    """ASTRA research contract over AETHON's bounded web research agent."""

    def __init__(self, search: Callable, fetch: Callable, *, max_sources: int = 5):
        self.agent = WebResearchAgent(search, fetch, max_sources=max_sources)

    def run(self, query: str) -> ResearchResult:
        report = self.agent.research(query)
        usable = [source for source in report.sources if source.url.startswith(("https://", "http://"))]
        domains = tuple(dict.fromkeys(source.domain for source in usable))
        return ResearchResult(report=report, verified_sources=len(usable), source_domains=domains)

    @staticmethod
    def format_citations(result: ResearchResult) -> list[dict[str, str]]:
        return [
            {"title": source.title, "url": source.url, "domain": source.domain,
             "evidence": (source.content or source.snippet)[:3000]}
            for source in result.report.sources
        ]

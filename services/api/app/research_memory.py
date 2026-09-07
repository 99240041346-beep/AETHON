from __future__ import annotations

import hashlib
from dataclasses import dataclass

from aethon.evidence_synthesis import EvidenceRecord, EvidenceSynthesizer
from aethon.memory_repository import MemoryRepository
from aethon.web_research import ResearchReport, WebResearchAgent


@dataclass(frozen=True)
class StoredResearch:
    report: ResearchReport
    stored_memory_ids: tuple[str, ...]
    skipped_sources: tuple[str, ...] = ()


class ResearchMemoryBridge:
    """Persist bounded web research as scoped, provenance-bearing memory.

    Web content is stored as contextual data. It is never promoted to executable
    instructions or authority. Every persisted record includes its source URL.
    """

    def __init__(self, researcher: WebResearchAgent, repository: MemoryRepository | None = None):
        self.researcher = researcher
        self.repository = repository or MemoryRepository()

    @staticmethod
    def _memory_id(url: str, query: str) -> str:
        digest = hashlib.sha256(f"{query.strip()}\n{url}".encode()).hexdigest()[:24]
        return f"research-{digest}"

    @staticmethod
    def _content(source) -> str:
        text = source.content.strip() or source.snippet.strip()
        return (
            f"Research source: {source.title or 'Untitled'}\n"
            f"URL: {source.url}\n"
            f"Evidence: {text[:10000]}"
        )

    def research_and_store(
        self,
        query: str,
        *,
        owner_id: str = "local-dev",
        project_id: str | None = None,
        namespace: str = "research",
    ) -> StoredResearch:
        report = self.researcher.research(query)
        stored: list[str] = []
        skipped: list[str] = []
        for source in report.sources:
            text = source.content.strip() or source.snippet.strip()
            if not text:
                skipped.append(source.url)
                continue
            memory_id = self._memory_id(source.url, report.query)
            try:
                self.repository.put(
                    memory_id,
                    self._content(source),
                    owner_id=owner_id,
                    project_id=project_id,
                    namespace=namespace,
                    memory_type="episodic",
                    source="web_research",
                    confidence=0.8 if source.content.strip() else 0.6,
                )
                stored.append(memory_id)
            except Exception:
                skipped.append(source.url)
        return StoredResearch(report, tuple(stored), tuple(skipped))

    def synthesize_from_report(self, report: ResearchReport, claims: list[str]):
        evidence = [
            EvidenceRecord(
                source_id=self._memory_id(source.url, report.query),
                url=source.url,
                title=source.title,
                excerpt=(source.content or source.snippet)[:10000],
                relevance=0.8 if source.content else 0.6,
                metadata={"query": report.query, "source": source.source},
            )
            for source in report.sources
        ]
        return EvidenceSynthesizer().synthesize(claims, evidence)

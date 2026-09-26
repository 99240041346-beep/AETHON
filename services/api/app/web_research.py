from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    content: str = ""
    authority_score: int = 0
    domain: str = ""


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

        raw_results = self.search(normalized, max(self.max_sources, 10)) or []
        sources: list[ResearchSource] = []
        limitations: list[str] = []
        seen_urls: set[str] = set()
        seen_domains: set[str] = set()

        candidates = []
        for item in list(raw_results):
            data = self._as_dict(item)
            url = str(data.get("url", "")).strip()
            if not url or not self._is_http_url(url):
                continue
            canonical = self._canonical_url(url)
            if canonical in seen_urls:
                continue
            seen_urls.add(canonical)
            domain = self._domain(url)
            authority = self._authority_score(domain, normalized)
            candidates.append((authority, domain, data, url))

        # Prefer authoritative sources for the subject, then diversify domains so
        # one site cannot consume the entire evidence set.
        candidates.sort(key=lambda item: (-item[0], item[1]))
        deferred = []
        for authority, domain, data, url in candidates:
            if len(sources) >= self.max_sources:
                break
            if domain in seen_domains and len(candidates) > self.max_sources:
                deferred.append((authority, domain, data, url))
                continue
            source = self._fetch_source(data, url, domain, authority, limitations)
            if source is not None:
                sources.append(source)
                seen_domains.add(domain)

        for authority, domain, data, url in deferred:
            if len(sources) >= self.max_sources:
                break
            source = self._fetch_source(data, url, domain, authority, limitations)
            if source is not None:
                sources.append(source)

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
        parsed = urlparse(url)
        return parsed.scheme in {"https", "http"} and bool(parsed.netloc)

    @staticmethod
    def _canonical_url(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/") or "/"
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.lower().split("@")[-1].split(":")[0]

    @staticmethod
    def _authority_score(domain: str, query: str) -> int:
        score = 0
        if domain.endswith(".gov.in") or domain.endswith(".gov"):
            score += 60
        elif domain.endswith(".nic.in"):
            score += 55
        elif domain.endswith(".edu") or domain.endswith(".ac.in"):
            score += 35
        elif domain.endswith(".org"):
            score += 15

        q = query.casefold()
        subject_domains = {
            "aadhaar": ("uidai.gov.in", 100),
            "pan card": ("incometax.gov.in", 100),
            "income tax": ("incometax.gov.in", 100),
            "gst": ("gst.gov.in", 100),
            "passport": ("passportindia.gov.in", 100),
            "election": ("eci.gov.in", 100),
        }
        for subject, (preferred, bonus) in subject_domains.items():
            if subject in q and (domain == preferred or domain.endswith("." + preferred)):
                score += bonus
        return score

    def _fetch_source(self, data: dict[str, Any], url: str, domain: str,
                      authority: int, limitations: list[str]) -> ResearchSource | None:
        title = str(data.get("title", "Untitled source")).strip()[:500]
        snippet = str(data.get("snippet", "")).strip()[:2000]
        source_name = str(data.get("source", "")).strip()[:200]
        content = ""
        try:
            fetched = self.fetch(url)
            content = self._extract_content(fetched)[: self.max_content_chars]
        except Exception as exc:
            limitations.append(f"Could not fetch {url}: {type(exc).__name__}")
        if not content and not snippet:
            return None
        return ResearchSource(title, url, snippet, source_name, content, authority, domain)

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

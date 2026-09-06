from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlparse

from aethon.evidence import Evidence, source_trust_score
from aethon.web import WebFetcher
from aethon.web_search import WebSearch


class RetrievalPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class CacheEntry:
    expires_at: float
    value: dict


class RetrievalCache:
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl_seconds = max(0.0, ttl_seconds)
        self._items: dict[str, CacheEntry] = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._items.get(key)
            if not entry:
                return None
            if entry.expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            return entry.value

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            self._items[key] = CacheEntry(time.monotonic() + self.ttl_seconds, value)


class RateLimiter:
    def __init__(self, min_interval_seconds: float = 0.25):
        self.min_interval = max(0.0, min_interval_seconds)
        self._last: dict[str, float] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            last = self._last.get(key, 0.0)
            if now - last < self.min_interval:
                raise RetrievalPolicyError("web retrieval rate limit exceeded")
            self._last[key] = now


class WebRetrievalService:
    """Resilient boundary around search/fetch with caching and provenance."""

    def __init__(self, search=None, fetch=None, cache=None, limiter=None):
        self.search = search or WebSearch()
        self.fetch = fetch or WebFetcher()
        self.cache = cache or RetrievalCache()
        self.limiter = limiter or RateLimiter()

    def search_web(self, query: str, limit: int = 5) -> list[dict]:
        query = query.strip()
        if not query:
            raise RetrievalPolicyError("search query must not be empty")
        key = f"search:{query.lower()}:{limit}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached["results"]
        self.limiter.check("search")
        results = self.search.search(query, limit)
        output = []
        for item in results:
            evidence = Evidence(
                title=item.title,
                url=item.url,
                snippet=item.snippet,
                source=item.source,
                trust_score=source_trust_score(item.url),
            )
            output.append({
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "source": item.source,
                "trust_score": evidence.trust_score,
                "evidence": evidence.__dict__,
            })
        self.cache.put(key, {"results": output})
        return output

    def fetch_url(self, url: str) -> dict:
        host = (urlparse(url).hostname or "").lower()
        if not host:
            raise RetrievalPolicyError("URL hostname is required")
        key = f"fetch:{url}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        self.limiter.check(f"fetch:{host}")
        result = self.fetch.fetch(url)
        evidence = Evidence(
            title=result.get("url", url),
            url=result.get("url", url),
            source="web_fetch",
            trust_score=source_trust_score(result.get("url", url)),
        ).with_content(result.get("text", ""))
        result = {**result, "trust_score": evidence.trust_score, "evidence": evidence.__dict__}
        self.cache.put(key, result)
        return result

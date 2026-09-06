from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from urllib.parse import urlparse


@dataclass(frozen=True)
class Evidence:
    title: str
    url: str
    snippet: str = ""
    source: str = "unknown"
    retrieved_at: str | None = None
    content_hash: str | None = None
    trust_score: float = 0.0

    def normalized_url(self) -> str:
        parsed = urlparse(self.url)
        host = (parsed.hostname or "").lower()
        path = parsed.path or "/"
        return f"{parsed.scheme.lower()}://{host}{path}".rstrip("/") or "/"

    def with_content(self, text: str) -> "Evidence":
        return Evidence(**{**asdict(self), "content_hash": sha256(text.encode("utf-8")).hexdigest()})


def source_trust_score(url: str) -> float:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(".gov") or host.endswith(".edu"):
        return 0.95
    if host.endswith(".org"):
        return 0.80
    if host.endswith(".com"):
        return 0.65
    return 0.50


def deduplicate_evidence(items: list[Evidence]) -> list[Evidence]:
    seen: set[str] = set()
    result: list[Evidence] = []
    for item in items:
        key = item.normalized_url()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def detect_conflicts(claims: list[tuple[str, str]]) -> list[dict[str, object]]:
    grouped: dict[str, set[str]] = {}
    for subject, value in claims:
        grouped.setdefault(subject.strip().lower(), set()).add(value.strip().lower())
    return [
        {"subject": subject, "values": sorted(values)}
        for subject, values in grouped.items()
        if len(values) > 1
    ]

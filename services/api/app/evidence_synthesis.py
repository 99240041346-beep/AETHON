from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class EvidenceRecord:
    source_id: str
    url: str
    title: str = ""
    excerpt: str = ""
    relevance: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Claim:
    text: str
    source_ids: tuple[str, ...] = ()
    supported: bool = False
    confidence: float = 0.0


@dataclass(frozen=True)
class SynthesisResult:
    answer: str
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...] = ()


class EvidenceSynthesizer:
    """Deterministic evidence gate for research outputs.

    This component does not treat source text as executable instructions. It only
    consumes bounded evidence records and requires every factual claim to name at
    least one supplied source before marking it supported.
    """

    def synthesize(self, claims: list[str], evidence: list[EvidenceRecord]) -> SynthesisResult:
        valid = {item.source_id: item for item in evidence if self._valid_source(item.url)}
        checked: list[Claim] = []
        limitations: list[str] = []
        for text in claims:
            normalized = text.strip()
            matches = tuple(
                source_id for source_id, item in valid.items()
                if self._supports(normalized, item)
            )
            confidence = min(1.0, max((valid[s].relevance for s in matches), default=0.0))
            checked.append(Claim(normalized, matches, bool(matches), confidence))
        if not valid:
            limitations.append("No valid HTTP(S) evidence sources were available.")
        unsupported = sum(1 for claim in checked if not claim.supported)
        if unsupported:
            limitations.append(f"{unsupported} claim(s) could not be grounded in the supplied evidence.")
        supported_text = [claim.text for claim in checked if claim.supported]
        answer = " ".join(supported_text)
        return SynthesisResult(answer=answer, claims=tuple(checked), limitations=tuple(limitations))

    @staticmethod
    def _valid_source(url: str) -> bool:
        try:
            return urlparse(url).scheme in {"http", "https"} and bool(urlparse(url).netloc)
        except Exception:
            return False

    @staticmethod
    def _supports(claim: str, evidence: EvidenceRecord) -> bool:
        haystack = f"{evidence.title} {evidence.excerpt}".lower()
        words = {word.strip(".,:;!?()[]{}\"").lower() for word in claim.split()}
        words = {word for word in words if len(word) > 3}
        if not words:
            return False
        return len(words & set(haystack.split())) >= max(1, min(3, len(words) // 3))

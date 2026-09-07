from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse
import re


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

    Source text is data, never executable instructions. Claims are supported only
    when a sufficiently large share of their meaningful terms occur in the same
    evidence record; short claims must match all meaningful terms.
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
            parsed = urlparse(url)
            return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
        except Exception:
            return False

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 3}

    @classmethod
    def _supports(cls, claim: str, evidence: EvidenceRecord) -> bool:
        claim_terms = cls._terms(claim)
        evidence_terms = cls._terms(f"{evidence.title} {evidence.excerpt}")
        if not claim_terms:
            return False
        overlap = len(claim_terms & evidence_terms)
        required = len(claim_terms) if len(claim_terms) <= 2 else (len(claim_terms) + 1) // 2
        return overlap >= required

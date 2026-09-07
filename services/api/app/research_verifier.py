from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SourceEvidence:
    source_id: str
    claim: str
    url: str
    confidence: float = 0.5


@dataclass(frozen=True)
class VerificationResult:
    supported: tuple[str, ...]
    disputed: tuple[str, ...]
    unsupported: tuple[str, ...]
    source_ids: tuple[str, ...]


class ResearchVerifier:
    """Deterministic, bounded cross-source verification.

    Evidence is data only. This component never executes or follows instructions
    contained in source material.
    """

    def __init__(self, *, max_claims: int = 20, min_support: float = 0.6) -> None:
        if not 1 <= max_claims <= 100:
            raise ValueError("max_claims must be between 1 and 100")
        if not 0.0 <= min_support <= 1.0:
            raise ValueError("min_support must be between 0 and 1")
        self.max_claims = max_claims
        self.min_support = min_support

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower())}

    def verify(self, claims: list[str], evidence: list[SourceEvidence]) -> VerificationResult:
        claims = [c.strip() for c in claims if c and c.strip()][: self.max_claims]
        supported: list[str] = []
        disputed: list[str] = []
        unsupported: list[str] = []
        used: list[str] = []

        for claim in claims:
            ct = self._tokens(claim)
            matches: list[SourceEvidence] = []
            for item in evidence:
                if not item.url.lower().startswith(("http://", "https://")):
                    continue
                et = self._tokens(item.claim)
                if not ct or not et:
                    continue
                overlap = len(ct & et) / len(ct)
                if overlap >= self.min_support:
                    matches.append(item)
            if not matches:
                unsupported.append(claim)
                continue

            positive = [m for m in matches if m.confidence >= self.min_support]
            negative = [m for m in matches if m.confidence < self.min_support]
            ids = [m.source_id for m in matches]
            for source_id in ids:
                if source_id not in used:
                    used.append(source_id)
            if positive and negative:
                disputed.append(claim)
            elif len({m.claim.strip().lower() for m in matches}) > 1:
                disputed.append(claim)
            else:
                supported.append(claim)

        return VerificationResult(tuple(supported), tuple(disputed), tuple(unsupported), tuple(used))

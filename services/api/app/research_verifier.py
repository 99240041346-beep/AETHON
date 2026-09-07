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
    """Bounded cross-source verifier; source material is data, never instructions."""
    def __init__(self, *, max_claims: int = 20, min_support: float = 0.6) -> None:
        if not 1 <= max_claims <= 100:
            raise ValueError("max_claims must be between 1 and 100")
        if not 0 <= min_support <= 1:
            raise ValueError("min_support must be between 0 and 1")
        self.max_claims, self.min_support = max_claims, min_support

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]{3,}", text.lower()))

    def verify(self, claims: list[str], evidence: list[SourceEvidence]) -> VerificationResult:
        supported, disputed, unsupported, used = [], [], [], []
        for claim in [c.strip() for c in claims if c and c.strip()][:self.max_claims]:
            ct = self._tokens(claim)
            matches = [e for e in evidence if e.url.lower().startswith(("http://", "https://")) and ct and (len(ct & self._tokens(e.claim)) / len(ct)) >= self.min_support]
            if not matches:
                unsupported.append(claim); continue
            for e in matches:
                if e.source_id not in used: used.append(e.source_id)
            if len({e.claim.strip().lower() for e in matches}) > 1:
                disputed.append(claim)
            else:
                supported.append(claim)
        return VerificationResult(tuple(supported), tuple(disputed), tuple(unsupported), tuple(used))

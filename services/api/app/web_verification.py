from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from aethon.evidence import Evidence, deduplicate_evidence, detect_conflicts


class VerificationStatus:
    SUPPORTED = "SUPPORTED"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class WebVerificationResult:
    status: str
    reason: str
    evidence_count: int
    conflicts: list[dict[str, object]]


class WebVerificationGate:
    """Conservative gate for claims derived from web evidence."""

    def __init__(self, minimum_sources: int = 1, minimum_trust: float = 0.5):
        self.minimum_sources = max(1, minimum_sources)
        self.minimum_trust = max(0.0, min(minimum_trust, 1.0))

    def verify(self, evidence: Iterable[Evidence], claims: list[tuple[str, str]] | None = None) -> WebVerificationResult:
        unique = deduplicate_evidence(list(evidence))
        usable = [item for item in unique if item.trust_score >= self.minimum_trust]
        conflicts = detect_conflicts(claims or [])
        if conflicts:
            return WebVerificationResult(VerificationStatus.CONFLICTED, "conflicting source claims require resolution", len(usable), conflicts)
        if len(usable) < self.minimum_sources:
            return WebVerificationResult(VerificationStatus.INSUFFICIENT_EVIDENCE, "not enough acceptable evidence", len(usable), [])
        return WebVerificationResult(VerificationStatus.SUPPORTED, "web evidence passed verification gate", len(usable), [])

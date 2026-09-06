from __future__ import annotations

from typing import Any

from aethon.evidence import Evidence
from aethon.verification import VerificationResult, Verifier
from aethon.web_verification import VerificationStatus, WebVerificationGate


class WebAwareVerifier:
    """Combines normal output verification with a conservative web-evidence gate.

    Ordinary model text keeps the existing AETHON-0 behavior. Structured results
    containing ``evidence`` are additionally required to pass web verification.
    """

    def __init__(self, base: Verifier, gate: WebVerificationGate | None = None):
        self.base = base
        self.gate = gate or WebVerificationGate()

    def verify(self, goal: str, result: Any) -> VerificationResult:
        basic = self.base.verify(goal, result)
        if not basic.ok:
            return basic
        if not isinstance(result, dict) or "evidence" not in result:
            return basic

        evidence = []
        for item in result.get("evidence", []):
            if isinstance(item, Evidence):
                evidence.append(item)
            elif isinstance(item, dict):
                evidence.append(Evidence(**item))

        claims = [tuple(claim) for claim in result.get("claims", []) if isinstance(claim, (list, tuple)) and len(claim) == 2]
        web_result = self.gate.verify(evidence, claims)
        evidence_data = {
            **basic.evidence,
            "web_verification": {
                "status": web_result.status,
                "reason": web_result.reason,
                "evidence_count": web_result.evidence_count,
                "conflicts": web_result.conflicts,
            },
        }
        if web_result.status != VerificationStatus.SUPPORTED:
            return VerificationResult(False, f"web verification failed: {web_result.reason}", evidence_data)
        return VerificationResult(True, "basic output and web evidence verification passed", evidence_data)

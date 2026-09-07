from __future__ import annotations

from dataclasses import dataclass

from aethon.research_memory import ResearchMemoryBridge
from aethon.research_loop import AutonomousResearchLoop, ResearchLoopResult
from aethon.research_verifier import ResearchVerifier, SourceEvidence, VerificationResult


@dataclass(frozen=True)
class ResearchAgentResult:
    loop: ResearchLoopResult
    verification: VerificationResult
    stored_memory_ids: tuple[str, ...]


class IntegratedResearchAgent:
    """Compose bounded research, cross-source verification, and episodic memory."""

    def __init__(self, loop: AutonomousResearchLoop, memory: ResearchMemoryBridge, verifier: ResearchVerifier):
        self.loop = loop
        self.memory = memory
        self.verifier = verifier

    def run(self, goal: str, *, owner_id: str = "local-dev", project_id: str | None = None,
            namespace: str = "research", max_questions: int = 5, max_rounds: int = 3) -> ResearchAgentResult:
        result = self.loop.run(goal, max_questions=max_questions, max_rounds=max_rounds)
        stored: list[str] = []
        evidence: list[SourceEvidence] = []
        claims: list[str] = []
        for report in result.rounds:
            stored_result = self.memory.research_and_store(
                report.query, owner_id=owner_id, project_id=project_id, namespace=namespace
            )
            stored.extend(stored_result.stored_memory_ids)
            for source in report.sources:
                evidence.append(SourceEvidence(
                    source_id=self.memory._memory_id(source.url, report.query),
                    claim=source.content or source.snippet,
                    url=source.url,
                    confidence=0.8 if source.content else 0.6,
                ))
            claims.extend(report.evidence)
        verification = self.verifier.verify(claims, evidence)
        return ResearchAgentResult(result, verification, tuple(dict.fromkeys(stored)))

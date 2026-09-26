from __future__ import annotations

"""ASTRA AI Factory: bounded specifications and lifecycle for generated agents."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from uuid import uuid4


class FactoryStage(str, Enum):
    SPECIFIED = "specified"
    GENERATED = "generated"
    SANDBOXED = "sandboxed"
    EVALUATED = "evaluated"
    REPAIR_REQUIRED = "repair_required"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    PAUSED = "paused"


@dataclass(frozen=True)
class AIAgentSpec:
    name: str
    goal: str
    capabilities: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    model: str = "provider-default"
    constraints: tuple[str, ...] = ()
    evaluation_cases: tuple[str, ...] = ()


@dataclass
class GeneratedAgent:
    agent_id: str
    spec: AIAgentSpec
    stage: FactoryStage = FactoryStage.SPECIFIED
    version: int = 1
    artifacts: dict[str, str] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)
    repair_count: int = 0


class AIFactory:
    """Orchestrates AI creation without executing generated code implicitly."""

    MAX_CAPABILITIES = 32
    MAX_TOOLS = 32
    MAX_EVAL_CASES = 128
    MAX_ARTIFACT_CHARS = 500_000

    def __init__(
        self,
        *,
        generator: Callable[[AIAgentSpec], dict[str, str]] | None = None,
        evaluator: Callable[[GeneratedAgent], dict[str, Any]] | None = None,
    ) -> None:
        self.generator = generator
        self.evaluator = evaluator
        self.agents: dict[str, GeneratedAgent] = {}

    def specify(self, spec: AIAgentSpec) -> GeneratedAgent:
        self._validate_spec(spec)
        agent = GeneratedAgent(str(uuid4()), spec)
        self.agents[agent.agent_id] = agent
        return agent

    def generate(self, agent_id: str) -> GeneratedAgent:
        agent = self._get(agent_id)
        if self.generator is None:
            raise RuntimeError("AI generator adapter is not configured")
        artifacts = self.generator(agent.spec)
        if not isinstance(artifacts, dict):
            raise ValueError("generator must return an artifact object")
        for key, value in artifacts.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("AI artifacts must be string keyed and string valued")
            if len(value) > self.MAX_ARTIFACT_CHARS:
                raise ValueError("generated artifact exceeds ASTRA bounds")
        agent.artifacts = dict(artifacts)
        agent.stage = FactoryStage.GENERATED
        return agent

    def sandbox(self, agent_id: str) -> GeneratedAgent:
        agent = self._get(agent_id)
        if agent.stage not in {FactoryStage.GENERATED, FactoryStage.REPAIR_REQUIRED}:
            raise ValueError("agent must be generated before sandboxing")
        agent.stage = FactoryStage.SANDBOXED
        return agent

    def evaluate(self, agent_id: str) -> GeneratedAgent:
        agent = self._get(agent_id)
        if agent.stage is not FactoryStage.SANDBOXED:
            raise ValueError("agent must be sandboxed before evaluation")
        if self.evaluator is None:
            raise RuntimeError("AI evaluator adapter is not configured")
        result = self.evaluator(agent)
        if not isinstance(result, dict):
            raise ValueError("evaluator must return an object")
        agent.evaluation = dict(result)
        passed = bool(result.get("passed", False))
        agent.stage = FactoryStage.EVALUATED if passed else FactoryStage.REPAIR_REQUIRED
        return agent

    def repair(self, agent_id: str, artifacts: dict[str, str]) -> GeneratedAgent:
        agent = self._get(agent_id)
        if agent.stage is not FactoryStage.REPAIR_REQUIRED:
            raise ValueError("agent is not awaiting repair")
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in artifacts.items()):
            raise ValueError("repair artifacts must be string keyed and string valued")
        if any(len(v) > self.MAX_ARTIFACT_CHARS for v in artifacts.values()):
            raise ValueError("repair artifact exceeds ASTRA bounds")
        agent.artifacts = dict(artifacts)
        agent.version += 1
        agent.repair_count += 1
        agent.stage = FactoryStage.GENERATED
        return agent

    def approve(self, agent_id: str) -> GeneratedAgent:
        agent = self._get(agent_id)
        if agent.stage is not FactoryStage.EVALUATED:
            raise ValueError("only evaluated agents can be approved")
        agent.stage = FactoryStage.APPROVED
        return agent

    def deploy(self, agent_id: str) -> GeneratedAgent:
        agent = self._get(agent_id)
        if agent.stage is not FactoryStage.APPROVED:
            raise ValueError("only approved agents can be deployed")
        agent.stage = FactoryStage.DEPLOYED
        return agent

    def pause(self, agent_id: str) -> GeneratedAgent:
        agent = self._get(agent_id)
        if agent.stage is not FactoryStage.DEPLOYED:
            raise ValueError("only deployed agents can be paused")
        agent.stage = FactoryStage.PAUSED
        return agent

    def _get(self, agent_id: str) -> GeneratedAgent:
        try:
            return self.agents[agent_id]
        except KeyError as exc:
            raise KeyError("unknown AI agent") from exc

    @classmethod
    def _validate_spec(cls, spec: AIAgentSpec) -> None:
        if not isinstance(spec.name, str) or not 1 <= len(spec.name.strip()) <= 120:
            raise ValueError("AI agent name is required")
        if not isinstance(spec.goal, str) or not 1 <= len(spec.goal.strip()) <= 4000:
            raise ValueError("AI agent goal is required")
        if len(spec.capabilities) > cls.MAX_CAPABILITIES:
            raise ValueError("too many capabilities")
        if len(spec.tools) > cls.MAX_TOOLS:
            raise ValueError("too many tools")
        if len(spec.evaluation_cases) > cls.MAX_EVAL_CASES:
            raise ValueError("too many evaluation cases")


__all__ = ["AIAgentSpec", "GeneratedAgent", "FactoryStage", "AIFactory"]

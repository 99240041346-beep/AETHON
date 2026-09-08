from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable


class SkillSecurityError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    version: str = "1"
    requires_approval: bool = False


@dataclass(frozen=True)
class SkillRequest:
    name: str
    input: str = ""
    requires_approval: bool = False


@dataclass(frozen=True)
class SkillResult:
    name: str
    success: bool
    output: str = ""
    error: str = ""


class SkillRegistry:
    def __init__(self, *, max_skills: int = 128, max_text: int = 12000) -> None:
        if not 1 <= max_skills <= 1000 or not 1 <= max_text <= 100000:
            raise ValueError("invalid skill bounds")
        self.max_skills = max_skills
        self.max_text = max_text
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        name = skill.name.strip()
        if not name or len(name) > 256 or len(skill.description) > self.max_text:
            raise SkillSecurityError("invalid skill metadata")
        key = name.casefold()
        if key not in self._skills and len(self._skills) >= self.max_skills:
            raise SkillSecurityError("skill registry budget exceeded")
        self._skills[key] = Skill(name, skill.description[: self.max_text], skill.version[:64], skill.requires_approval)

    def get(self, name: str) -> Skill:
        skill = self._skills.get(name.strip().casefold())
        if skill is None:
            raise SkillSecurityError("skill is not registered")
        return skill

    def names(self) -> tuple[str, ...]:
        return tuple(skill.name for skill in self._skills.values())


class BoundedSkillSystem:
    """Deterministic skill selection and execution boundary; skills remain untrusted capabilities."""

    def __init__(self, registry: SkillRegistry, *, max_requests: int = 32, max_input: int = 12000, max_output: int = 12000) -> None:
        if not 1 <= max_requests <= 128 or not 1 <= max_input <= 100000 or not 1 <= max_output <= 100000:
            raise ValueError("invalid skill execution bounds")
        self.registry = registry
        self.max_requests = max_requests
        self.max_input = max_input
        self.max_output = max_output

    def validate(self, requests: Iterable[SkillRequest]) -> tuple[SkillRequest, ...]:
        values = tuple(requests)
        if len(values) > self.max_requests:
            raise SkillSecurityError("skill request budget exceeded")
        for request in values:
            self.registry.get(request.name)
            if len(request.input) > self.max_input:
                raise SkillSecurityError("skill input exceeds bounds")
        return values

    def execute(self, requests: Iterable[SkillRequest], handlers: dict[str, Callable[[str], str]], *, approve: bool = False) -> tuple[SkillResult, ...]:
        results: list[SkillResult] = []
        for request in self.validate(requests):
            skill = self.registry.get(request.name)
            if (skill.requires_approval or request.requires_approval) and not approve:
                results.append(SkillResult(skill.name, False, error="approval required"))
                continue
            handler = handlers.get(skill.name.casefold())
            if handler is None:
                results.append(SkillResult(skill.name, False, error="skill handler is unavailable"))
                break
            try:
                output = str(handler(request.input))[: self.max_output]
            except Exception as exc:
                results.append(SkillResult(skill.name, False, error=str(exc)[:1000]))
                break
            results.append(SkillResult(skill.name, True, output=output))
        return tuple(results)

    def plan(self, goal: str) -> tuple[SkillRequest, ...]:
        if not goal.strip():
            raise SkillSecurityError("skill goal is required")
        return ()


__all__ = ["BoundedSkillSystem", "Skill", "SkillRegistry", "SkillRequest", "SkillResult", "SkillSecurityError"]

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .agent_brain import AgentBrain, Plan, PlanStep, StepKind


@dataclass(frozen=True)
class GoalAnalysis:
    objective: str
    complexity: str
    requires_web: bool
    requires_tools: bool


class IntelligencePlanner:
    """Model-assisted planner with strict parsing and deterministic fallback."""

    def __init__(self, model, brain: AgentBrain | None = None):
        self.model = model
        self.brain = brain or AgentBrain()

    def analyze(self, goal: str, tool_names: set[str]) -> GoalAnalysis:
        lowered = goal.lower()
        requires_web = any(word in lowered for word in ("search", "latest", "research", "find", "news", "source")) and "web_search" in tool_names
        requires_tools = bool(tool_names) and any(word in lowered for word in ("search", "fetch", "open", "create", "run", "execute", "check", "find"))
        complexity = "high" if len(goal.split()) > 35 or any(x in lowered for x in ("compare", "analyze", "research", "build", "multiple")) else "medium" if len(goal.split()) > 12 else "low"
        return GoalAnalysis(goal.strip(), complexity, requires_web, requires_tools)

    def create_plan(self, goal: str, tool_names: set[str]) -> Plan:
        analysis = self.analyze(goal, tool_names)
        try:
            parsed = self._parse(self.model.generate(self._prompt(analysis, tool_names)))
            if parsed:
                return self._validated_plan(goal, parsed, tool_names)
        except Exception:
            pass
        return self.brain.initial_plan(goal, tool_names)

    @staticmethod
    def _prompt(analysis: GoalAnalysis, tool_names: set[str]) -> str:
        tools = ", ".join(sorted(tool_names)) or "none"
        return ("You are AETHON's planning module. Return ONLY valid JSON. "
                "Do not execute actions or claim actions occurred. Create a bounded plan of at most 8 steps. "
                "Each step needs step_id, description, kind (REASON|TOOL|VERIFY), tool, arguments, depends_on. "
                f"Goal: {analysis.objective}\nComplexity: {analysis.complexity}\nAvailable tools: {tools}\n"
                "Use VERIFY for externally grounded or consequential conclusions.")

    @staticmethod
    def _parse(raw: str) -> list[dict[str, Any]] | None:
        text = raw.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].lstrip()
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(value, dict):
            value = value.get("steps")
        return value if isinstance(value, list) else None

    def _validated_plan(self, goal: str, raw_steps: list[dict[str, Any]], tools: set[str]) -> Plan:
        steps: list[PlanStep] = []
        seen: set[str] = set()
        for index, item in enumerate(raw_steps[:8], 1):
            if not isinstance(item, dict):
                continue
            step_id = str(item.get("step_id") or f"step-{index}")
            if step_id in seen:
                continue
            try:
                kind = StepKind(str(item.get("kind", "REASON")).upper())
            except ValueError:
                kind = StepKind.REASON
            tool = str(item["tool"]) if item.get("tool") is not None else None
            if kind == StepKind.TOOL and tool not in tools:
                kind, tool = StepKind.REASON, None
            depends = [str(x) for x in item.get("depends_on", []) if str(x) in seen]
            arguments = item.get("arguments", {})
            if not isinstance(arguments, dict):
                arguments = {}
            steps.append(PlanStep(step_id, str(item.get("description") or "Execute planned reasoning step"), kind, tool, arguments, depends))
            seen.add(step_id)
        if not steps:
            return self.brain.initial_plan(goal, tools)
        if steps[-1].kind != StepKind.VERIFY:
            steps.append(PlanStep(f"step-{len(steps)+1}", "Verify the candidate result", StepKind.VERIFY, depends_on=[steps[-1].step_id]))
        return Plan(goal=goal.strip(), steps=steps[: self.brain.max_steps])

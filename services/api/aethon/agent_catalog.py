from __future__ import annotations

from dataclasses import replace
from .astra_core import AgentDefinition, Permission

READ = (Permission.READ,)
WRITE = (Permission.READ, Permission.WRITE)
EXECUTE = (Permission.READ, Permission.EXECUTE)
EXTERNAL = (Permission.READ, Permission.EXTERNAL_ACTION)

BUILTIN_AGENTS = {
    "research": AgentDefinition("research", "ResearchAgent", "Find, compare and synthesize sourced information.", tools=("web_search", "web_fetch", "web_research"), permissions=READ, max_steps=16),
    "coding": AgentDefinition("coding", "CodingAgent", "Inspect, patch and verify source code in a bounded workspace.", tools=("files.read", "files.patch", "sandbox.test"), permissions=EXECUTE, max_steps=24),
    "data": AgentDefinition("data", "DataAgent", "Analyze structured datasets and produce verified results.", tools=("data_analyze", "chart"), permissions=READ, max_steps=16),
    "document": AgentDefinition("document", "DocumentAgent", "Generate and validate user-requested documents.", tools=("files.read", "document.generate"), permissions=WRITE, max_steps=12),
    "writing": AgentDefinition("writing", "WritingAgent", "Draft, rewrite and review user-provided content.", tools=("context.read",), permissions=READ, max_steps=10),
    "study": AgentDefinition("study", "StudyAgent", "Teach, quiz and track study-session outputs.", tools=("context.read",), permissions=READ, max_steps=12),
    "project": AgentDefinition("project", "ProjectAgent", "Plan project work and maintain project outputs.", tools=("project.read", "task.create", "project.write"), permissions=WRITE, max_steps=20),
    "automation": AgentDefinition("automation", "AutomationAgent", "Plan bounded automations without silently executing side effects.", tools=("automation.read", "automation.write"), permissions=WRITE, max_steps=16),
    "ai-orchestrator": AgentDefinition("ai-orchestrator", "AIOrchestratorAgent", "Route work across configured AI providers and connected creation services.", tools=("ai.providers", "ai.generate", "web_research", "creation.dispatch"), permissions=EXECUTE, max_steps=24),
    "creator": AgentDefinition("creator", "CreatorAgent", "Turn requirements into code, websites and media through configured providers.", tools=("ai.generate", "creation.dispatch", "deployment.verify"), permissions=EXECUTE, max_steps=24),
}


def get_builtin_agent(name: str) -> AgentDefinition:
    try:
        return replace(BUILTIN_AGENTS[name.lower()])
    except KeyError as exc:
        raise KeyError(f"unknown built-in agent: {name}") from exc

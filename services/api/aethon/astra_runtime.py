from __future__ import annotations

"""ASTRA facade over the existing AETHON runtime.

ASTRA is the product-level contract; AETHON remains the execution foundation.
This module intentionally delegates execution to the established bounded
AgentRuntime/ToolRegistry so we do not create a second execution engine.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from aethon.agent import AgentRuntime
from aethon.agent_catalog import BUILTIN_AGENTS, get_builtin_agent
from aethon.schemas import Task, TaskStatus
from app.tools import ToolRegistry


@dataclass(frozen=True)
class ASTRAAgentInfo:
    id: str
    name: str
    description: str
    tools: tuple[str, ...]
    max_steps: int
    max_tool_calls: int


class ASTRARuntime:
    """Product facade for agent discovery and bounded task execution."""

    def __init__(self, *, agent_runtime: AgentRuntime | None = None,
                 tools: ToolRegistry | None = None) -> None:
        self.tools = tools or ToolRegistry()
        self.agent_runtime = agent_runtime or AgentRuntime(tools=self.tools)

    def agents(self) -> list[ASTRAAgentInfo]:
        return [
            ASTRAAgentInfo(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                tools=definition.tools,
                max_steps=definition.max_steps,
                max_tool_calls=definition.max_tool_calls,
            )
            for definition in BUILTIN_AGENTS.values()
        ]

    def agent(self, agent_id: str) -> ASTRAAgentInfo:
        definition = get_builtin_agent(agent_id)
        return ASTRAAgentInfo(
            definition.id, definition.name, definition.description,
            definition.tools, definition.max_steps, definition.max_tool_calls,
        )

    def run(self, *, agent_id: str, goal: str, owner_id: str,
            project_id: str | None = None, priority: int = 5,
            task_id: UUID | None = None) -> Task:
        definition = get_builtin_agent(agent_id)
        if not goal.strip():
            raise ValueError("goal cannot be empty")
        # The current AETHON AgentRuntime performs the actual planning,
        # authorization, execution, checkpointing and verification. The
        # definition is used here to validate the requested ASTRA agent.
        task = Task(
            task_id=task_id or uuid4(),
            goal=goal.strip(),
            project_id=project_id,
            priority=priority,
            owner_id=owner_id,
            status=TaskStatus.QUEUED,
        )
        # Fail early for catalog entries whose declared tools are not present;
        # this prevents an agent from appearing executable when its capability
        # adapter has not been installed yet.
        available = {spec.name for spec in self.tools.list()}
        missing = sorted(set(definition.tools) - available)
        if missing:
            task.status = TaskStatus.FAILED
            task.error = "agent capability adapters unavailable: " + ", ".join(missing)
            return task
        return self.agent_runtime.run(task)

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskNode:
    id: str
    goal: str
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskGraph:
    nodes: tuple[TaskNode, ...]

    def ready(self, completed: set[str]) -> tuple[TaskNode, ...]:
        return tuple(
            node
            for node in self.nodes
            if node.id not in completed
            and all(dependency in completed for dependency in node.depends_on)
        )


class TaskGraphPlanner:
    """Build a bounded, deterministic dependency graph from explicit subgoals."""

    def __init__(self, *, max_nodes: int = 20) -> None:
        if not 1 <= max_nodes <= 100:
            raise ValueError("max_nodes must be between 1 and 100")
        self.max_nodes = max_nodes

    def build(
        self,
        subgoals: list[str],
        dependencies: dict[str, list[str]] | None = None,
    ) -> TaskGraph:
        dependencies = dependencies or {}
        cleaned: list[str] = []
        seen: set[str] = set()

        for goal in subgoals:
            value = goal.strip()
            key = value.casefold()
            if value and key not in seen and len(cleaned) < self.max_nodes:
                seen.add(key)
                cleaned.append(value)

        ids = {goal: f"task-{index + 1}" for index, goal in enumerate(cleaned)}
        nodes: list[TaskNode] = []
        for goal in cleaned:
            deps = tuple(
                ids[dependency.strip()]
                for dependency in dependencies.get(goal, [])
                if dependency.strip() in ids and dependency.strip() != goal
            )
            nodes.append(TaskNode(ids[goal], goal[:500], deps))

        return TaskGraph(tuple(nodes))

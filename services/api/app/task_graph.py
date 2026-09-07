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
        return tuple(n for n in self.nodes if n.id not in completed and all(d in completed for d in n.depends_on))


class TaskGraphPlanner:
    def __init__(self, *, max_nodes: int = 20) -> None:
        if not 1 <= max_nodes <= 100:
            raise ValueError("max_nodes must be between 1 and 100")
        self.max_nodes = max_nodes

    def build(self, subgoals: list[str], dependencies: dict[str, list[str]] | None = None) -> TaskGraph:
        dependencies = dependencies or {}
        cleaned: list[str] = []
        seen: set[str] = set()
        for goal in subgoals:
            value = goal.strip()
            key = value.casefold()
            if value and key not in seen and len(cleaned) < self.max_nodes:
                seen.add(key)
                cleaned.append(value)
        ids = {goal: f"task-{i + 1}" for i, goal in enumerate(cleaned)}
        nodes = [TaskNode(ids[g], g[:500], tuple(ids[d.strip()] for d in dependencies.get(g, []) if d.strip() in ids)) for g in cleaned]
        return TaskGraph(tuple(nodes))

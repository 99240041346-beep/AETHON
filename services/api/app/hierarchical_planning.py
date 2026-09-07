from __future__ import annotations

from dataclasses import dataclass


_LEVELS = ("goal", "mission", "objective", "subgoal", "task", "action")


@dataclass(frozen=True)
class PlanNode:
    id: str
    level: str
    description: str
    parent_id: str | None = None
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class HierarchicalPlan:
    nodes: tuple[PlanNode, ...]

    def children(self, parent_id: str) -> tuple[PlanNode, ...]:
        return tuple(node for node in self.nodes if node.parent_id == parent_id)

    def at_level(self, level: str) -> tuple[PlanNode, ...]:
        if level not in _LEVELS:
            raise ValueError(f"unknown level: {level}")
        return tuple(node for node in self.nodes if node.level == level)

    def ready(self, completed: set[str]) -> tuple[PlanNode, ...]:
        return tuple(
            node
            for node in self.nodes
            if node.id not in completed
            and all(dependency in completed for dependency in node.depends_on)
        )


class HierarchicalPlanner:
    """Build bounded, deterministic goal-to-action planning hierarchies.

    Planning output is advisory data. It never authorizes tools, changes risk,
    or bypasses the Safety Kernel or execution verification.
    """

    def __init__(
        self,
        *,
        max_depth: int = 6,
        max_branching: int = 5,
        max_nodes: int = 100,
        max_description_length: int = 500,
    ) -> None:
        if not 1 <= max_depth <= len(_LEVELS):
            raise ValueError("max_depth must be between 1 and 6")
        if not 1 <= max_branching <= 20:
            raise ValueError("max_branching must be between 1 and 20")
        if not 1 <= max_nodes <= 1000:
            raise ValueError("max_nodes must be between 1 and 1000")
        if not 1 <= max_description_length <= 2000:
            raise ValueError("max_description_length must be between 1 and 2000")
        self.max_depth = max_depth
        self.max_branching = max_branching
        self.max_nodes = max_nodes
        self.max_description_length = max_description_length

    def build(self, goal: str, hierarchy: dict[str, list[str]] | None = None) -> HierarchicalPlan:
        root = goal.strip()
        if not root:
            raise ValueError("goal must not be empty")

        hierarchy = hierarchy or {}
        nodes: list[PlanNode] = [PlanNode("level-1-1", "goal", root[: self.max_description_length])]
        frontier = [nodes[0]]

        for depth in range(1, self.max_depth):
            if not frontier or len(nodes) >= self.max_nodes:
                break
            next_frontier: list[PlanNode] = []
            level = _LEVELS[depth]
            for parent in frontier:
                seen: set[str] = set()
                accepted = 0
                for raw in hierarchy.get(parent.description, []):
                    description = raw.strip()
                    key = description.casefold()
                    if not description or key in seen:
                        continue
                    seen.add(key)
                    if accepted >= self.max_branching or len(nodes) >= self.max_nodes:
                        break
                    accepted += 1
                    node = PlanNode(
                        id=f"level-{depth + 1}-{accepted}-{len(nodes) + 1}",
                        level=level,
                        description=description[: self.max_description_length],
                        parent_id=parent.id,
                    )
                    nodes.append(node)
                    next_frontier.append(node)
            frontier = next_frontier

        return HierarchicalPlan(tuple(nodes))

    def replan(
        self,
        plan: HierarchicalPlan,
        failed_node_id: str,
        alternatives: list[str],
    ) -> HierarchicalPlan:
        failed = next((node for node in plan.nodes if node.id == failed_node_id), None)
        if failed is None:
            raise ValueError("failed_node_id does not exist")
        if failed.level == "goal":
            raise ValueError("root goal cannot be replaced by a local alternative")

        prefix = list(plan.nodes)
        existing = {node.description.casefold() for node in prefix}
        additions: list[PlanNode] = []
        for index, raw in enumerate(alternatives, start=1):
            value = raw.strip()
            if not value or value.casefold() in existing:
                continue
            if len(additions) >= self.max_branching or len(prefix) + len(additions) >= self.max_nodes:
                break
            additions.append(
                PlanNode(
                    id=f"replan-{failed.id}-{len(additions) + 1}",
                    level=failed.level,
                    description=value[: self.max_description_length],
                    parent_id=failed.parent_id,
                )
            )
            existing.add(value.casefold())
        return HierarchicalPlan(tuple(prefix + additions))


__all__ = ["HierarchicalPlan", "HierarchicalPlanner", "PlanNode"]

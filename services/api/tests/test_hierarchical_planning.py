import pytest

from app.hierarchical_planning import HierarchicalPlanner


def test_builds_deterministic_goal_to_action_hierarchy() -> None:
    planner = HierarchicalPlanner(max_depth=3, max_branching=2)
    plan = planner.build(
        "Ship feature",
        {
            "Ship feature": ["Plan work", "Implement"],
            "Plan work": ["Research"],
            "Implement": ["Code"],
        },
    )
    assert [(node.level, node.description) for node in plan.nodes] == [
        ("goal", "Ship feature"),
        ("mission", "Plan work"),
        ("mission", "Implement"),
        ("objective", "Research"),
        ("objective", "Code"),
    ]
    assert plan.nodes[1].parent_id == plan.nodes[0].id


def test_branching_and_total_node_bounds_are_enforced() -> None:
    planner = HierarchicalPlanner(max_depth=6, max_branching=2, max_nodes=4)
    plan = planner.build("G", {"G": ["A", "B", "C"]})
    assert len(plan.nodes) == 3
    assert [node.description for node in plan.nodes] == ["G", "A", "B"]


def test_empty_and_duplicate_children_are_dropped_deterministically() -> None:
    planner = HierarchicalPlanner(max_depth=2, max_branching=5)
    plan = planner.build("G", {"G": [" A ", "a", "", "B"]})
    assert [node.description for node in plan.children("level-1-1")] == ["A", "B"]


def test_invalid_bounds_are_rejected() -> None:
    with pytest.raises(ValueError):
        HierarchicalPlanner(max_depth=0)
    with pytest.raises(ValueError):
        HierarchicalPlanner(max_branching=0)
    with pytest.raises(ValueError):
        HierarchicalPlanner(max_nodes=0)


def test_dependency_readiness_is_deterministic() -> None:
    planner = HierarchicalPlanner(max_depth=2)
    plan = planner.build("G", {"G": ["A", "B"]})
    first = plan.children("level-1-1")
    dependent = first[1]
    plan_with_dependency = type(plan)(
        plan.nodes[:2]
        + (dependent.__class__(dependent.id, dependent.level, dependent.description, dependent.parent_id, (first[0].id,)),)
    )
    assert [node.id for node in plan_with_dependency.ready(set())] == [first[0].id]
    assert [node.id for node in plan_with_dependency.ready({first[0].id})] == [first[1].id]


def test_replan_adds_bounded_alternatives_without_authority() -> None:
    planner = HierarchicalPlanner(max_depth=2, max_branching=2, max_nodes=4)
    plan = planner.build("G", {"G": ["A"]})
    replanned = planner.replan(plan, "level-2-1-2", ["Fallback", "Fallback", "Second"])
    assert [node.description for node in replanned.nodes] == ["G", "A", "Fallback", "Second"]
    assert replanned.nodes[-1].parent_id == plan.nodes[0].id


def test_unknown_failed_node_is_rejected() -> None:
    with pytest.raises(ValueError):
        HierarchicalPlanner().replan(HierarchicalPlanner().build("G"), "missing", ["A"])

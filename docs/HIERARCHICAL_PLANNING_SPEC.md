# AETHON 17V — Hierarchical Planning

## Purpose

17V adds a bounded hierarchy from a user goal through mission, objective, subgoal, task, and action planning levels. The planner is advisory and deterministic.

## Contract

- `PlanNode` contains an immutable id, level, description, optional parent, and dependencies.
- `HierarchicalPlan` exposes deterministic children, level, and readiness queries.
- `HierarchicalPlanner` bounds depth, branching, total nodes, and description length.
- Empty and case-insensitive duplicate siblings are removed deterministically.
- Unknown dependencies cannot become authorization or readiness grants.
- Replanning is bounded to local alternatives and cannot replace the root goal.

## Execution boundary

```text
Hierarchy
  -> Task Graph
  -> Safety Kernel
  -> Authorization
  -> 17U bounded execution
  -> Verification
```

Planning, historical experience, model output, and replanning must not authorize tools, change permissions or risk classification, bypass approval, expose secrets, or suppress verification.

## Failure and replanning

A failed non-root node may receive a bounded list of local alternatives. Alternatives inherit the failed node's level and parent. Existing descriptions are not duplicated. Replanning does not mark an alternative successful; execution and verification remain separate.

## Determinism

Input order is preserved. Sibling deduplication is case-insensitive. Branching and node-count limits are enforced before adding a node. IDs are derived from depth, accepted sibling order, and global insertion order.

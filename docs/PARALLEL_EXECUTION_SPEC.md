# 17U — Parallel Task Execution Specification

## Purpose

17U executes the bounded dependency graph produced by 17T. It provides concurrency without turning planning data into authority.

## Contract

`ParallelTaskExecutor` accepts a `TaskGraph`, a task handler, a safety gate, and a verifier. It schedules dependency-ready nodes in deterministic graph order while allowing independent nodes to run concurrently.

## Guarantees

- Maximum worker count is bounded to 32.
- Total graph work is bounded by `max_tasks`.
- Retries are bounded by `max_retries`.
- Overall execution has a bounded deadline.
- A task is checked by the supplied Safety Kernel adapter immediately before submission.
- A safety rejection never invokes the handler.
- A task is successful only when its verifier returns true.
- Failed dependencies block their dependents.
- Independent tasks may continue after an unrelated task fails.
- Results are returned in graph order, not completion order.
- Cancellation is cooperative and prevents new work from being submitted.

## Safety Boundary

The executor does not implement or replace authorization. The supplied `safety_check` remains the authoritative policy boundary. A task graph, handler result, retry, or scheduler decision cannot grant permissions.

Recommended integration:

```text
TaskGraph
   ↓
Ready Tasks
   ↓
Safety Kernel adapter
   ↓
Bounded executor
   ↓
Tool/runtime handler
   ↓
Verifier
   ↓
Task result
```

## Failure Semantics

- Handler exception → retry up to the configured limit, then `FAILED`.
- Verification failure → retry up to the configured limit, then `FAILED`.
- Failed dependency → dependent becomes `BLOCKED`.
- Safety rejection → task becomes `REJECTED` and is never executed.
- Cancellation/deadline → remaining unscheduled work becomes `CANCELLED`.
- Cycles or unresolved dependencies → remaining work becomes `BLOCKED`.

17U deliberately does not mutate permissions, risk classifications, approvals, memory authority, or Safety Kernel state.

# AETHON Agent Runtime Specification

## Purpose

Define deterministic runtime behavior around model calls, planning, tools, verification, recovery, resumability, and concurrent scheduling.

## State Machine

```text
QUEUED → PLANNING → EXECUTING → VERIFYING → SUCCEEDED
             │          │           │
             │          ├───────────┘
             │          ↓
             │       REPLANNING
             ↓
      AWAITING_APPROVAL
             │
             ↓
           PAUSED ─────────→ EXECUTING

Any active state → CANCELLED
Recoverable failure → REPLANNING or retry
Terminal failure → FAILED
Policy violation → BLOCKED
```

## Runtime Rules

1. A task has exactly one authoritative lifecycle state.
2. Every transition emits an event.
3. A model can propose actions but cannot authorize them.
4. Every tool call is validated against its declared schema.
5. Side effects are policy-checked before execution.
6. Tool calls are time-bounded and cancellable where technically possible.
7. Verification must inspect evidence rather than trusting the model's claim of success.
8. Retries are bounded and respect idempotency.
9. Cancellation prevents new side effects after the cancellation boundary.
10. Secrets never enter model context unless explicitly approved by the security layer.
11. Scheduler concurrency is bounded by an explicit worker limit.
12. Task priority affects scheduling order only and cannot bypass security policy.
13. Pausing occurs at a safe checkpoint; in-flight non-cancellable work reaches its boundary first.
14. Resume restores the persisted plan, observations, approvals, last verified step, and recovery history.

## Scheduler

AETHON uses a bounded priority scheduler for concurrent agent tasks:

```text
Task request
    ↓
Priority queue
    ↓
Bounded worker pool
 ┌──────┬──────┬──────┐
Agent  Agent  Agent  ...
 └──────┴──────┴──────┘
    ↓
Durable checkpoints
```

Lower numeric priority values execute first. Equal priorities retain FIFO ordering. The worker limit is configured with `AETHON_MAX_CONCURRENT_TASKS` and defaults to four.

The scheduler is an execution mechanism, not an authorization mechanism. Every worker still runs through the normal Safety Kernel, verification, audit, and recovery controls.

## Planning

The planner produces a bounded plan. Each step contains intent, required capability, candidate tool, expected observation, risk, and completion criteria.

The planner may replan when observations contradict assumptions, a tool fails, or verification fails. Replanning must preserve task constraints and security policy.

## Execution Loop

```text
while task is active:
    check cooperative pause control
    if pause requested:
        checkpoint plan + observations + approvals + recovery history
        transition to PAUSED
        return
    observe current state
    select next plan step
    validate tool/model request
    evaluate policy
    request approval when required
    execute within limits
    record observation
    verify result
    checkpoint
    continue, retry, replan, ask, block, or finish
```

## Durable State

A resumable checkpoint contains:

- task ID
- current plan and revision
- completed steps
- observations
- approvals
- recovery history
- last verified step
- lifecycle/checkpoint status
- update timestamp

The checkpoint is execution state, not user memory. It is restored only for the same authorized task/owner scope.

## Recovery

Recoverable failures include transient network failures, provider unavailability, malformed tool output, and verification failure. Recovery must use bounded retries and alternative strategies only when allowed by policy.

Repeated failure should terminate with a structured diagnostic rather than looping indefinitely.

## Human Interaction

The runtime asks the user when a decision is ambiguous, required information is missing, or policy requires approval. Approval requests must describe the proposed action, affected resource, risk, and reversibility.

## Cancellation

Cancellation is first-class. A task may be cancelled by the user or system policy. Running tools should receive cancellation where supported. The runtime must record whether cancellation occurred before or after an external side effect.

## Pause and Resume

`POST /v1/tasks/{task_id}/pause` requests a cooperative pause. The request is persisted separately from the checkpoint so a process restart cannot silently lose it. The runtime honors it at the next safe checkpoint boundary and persists status `PAUSED`.

`POST /v1/tasks/{task_id}/resume` is valid only for a paused task with persisted agent state. It clears the pause control, reconstructs the plan, restores observations and recovery history, and resumes execution. Terminal tasks cannot be resumed.

The current AETHON-0 HTTP execution path is synchronous; therefore pause is cooperative rather than a forced thread/process interrupt. Distributed workers and queue-backed execution can later use the same durable control contract.

## Runtime Invariants

- No unauthorized side effect.
- No unbounded autonomous loop.
- No silent state transition.
- No successful status without verification criteria being satisfied.
- No cross-project memory access without authorization.
- No concurrency setting may override policy or resource limits.
- No resume without an authorized persisted checkpoint.
- No forced interruption in the middle of an unsafe/non-cancellable side effect.

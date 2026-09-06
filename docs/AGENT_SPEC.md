# AETHON Agent Runtime Specification

## Purpose

Define the deterministic runtime behavior around model calls, planning, tools, verification, and recovery.

## State Machine

```text
QUEUED → PLANNING → EXECUTING → VERIFYING → SUCCEEDED
             │          │           │
             │          ├───────────┘
             │          ↓
             │       REPLANNING
             ↓
      AWAITING_APPROVAL

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

## Planning

The planner produces a bounded plan. Each step contains intent, required capability, candidate tool, expected observation, risk, and completion criteria.

The planner may replan when observations contradict assumptions, a tool fails, or verification fails. Replanning must preserve task constraints and security policy.

## Execution Loop

```text
while task is active:
    observe current state
    select next plan step
    validate tool/model request
    evaluate policy
    request approval when required
    execute within limits
    record observation
    verify result
    continue, retry, replan, ask, block, or finish
```

## Recovery

Recoverable failures include transient network failures, provider unavailability, malformed tool output, and verification failure. Recovery must use bounded retries and alternative strategies only when allowed by policy.

Repeated failure should terminate with a structured diagnostic rather than looping indefinitely.

## Human Interaction

The runtime asks the user when a decision is ambiguous, required information is missing, or policy requires approval. Approval requests must describe the proposed action, affected resource, risk, and reversibility.

## Cancellation

Cancellation is first-class. A task may be cancelled by the user or system policy. Running tools should receive cancellation where supported. The runtime must record whether cancellation occurred before or after an external side effect.

## Runtime Invariants

- No unauthorized side effect.
- No unbounded autonomous loop.
- No silent state transition.
- No successful status without verification criteria being satisfied.
- No cross-project memory access without authorization.

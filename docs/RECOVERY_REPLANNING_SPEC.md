# AETHON 17W — Advanced Recovery & Replanning

## Purpose

17W adds a deterministic recovery policy above distributed task reclamation. It classifies failures, applies bounded retry/backoff budgets, proposes bounded local replans, and stops conservatively when recovery is unsafe or exhausted.

## Safety boundary

Recovery and replanning are advisory execution controls. A safety denial is terminal for recovery: no retry, replan, delay, or alternative may override the Safety Kernel. Execution remains subject to the existing authorization and verification path.

## Recovery policy

- `max_attempts` bounds retries.
- `max_replans` bounds local replanning attempts.
- Exponential backoff is deterministic and capped; no unbounded waiting or jitter is introduced by the policy.
- `max_recovery_seconds` provides a hard recovery deadline.
- Permanent and unknown failures abort conservatively.
- Cancellation is terminal.

## Replanning

Alternatives are stripped, case-insensitively deduplicated, length-limited, and capped. The policy never executes an alternative itself or changes permissions/risk.

## Verification

A recovery action is not reported as `RECOVERED` unless it was executed and verification passed. Failed verification remains a recovery failure and may consume the bounded recovery budget.

## Determinism

Given the same failure class, counters, policy, elapsed time, and safety decision, the planner returns the same decision and delay. This makes recovery behavior testable and auditable.

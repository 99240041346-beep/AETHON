# AETHON Agent Learning Specification

## Purpose

The Agent Learning Layer converts verified task outcomes into small, bounded, auditable memory signals. It improves future context without changing the Safety Kernel, permissions, or execution policy.

## Learning contract

A learning signal contains:

- `kind`: signal category.
- `value`: bounded human-readable content.
- `confidence`: normalized confidence from `0.0` to `1.0`.

The default extractor creates a `verified_outcome` signal only when a task has a successful verification step and a non-empty result.

## Memory lifecycle

1. A task executes through the normal Agent Brain runtime.
2. A verifier produces successful verification evidence.
3. The task result is stored as episodic memory using the task owner/project/namespace scope.
4. The learning layer extracts bounded signals from that verified result.
5. Signals are deduplicated and stored as semantic memory with source `agent_learning`.
6. Learning telemetry is emitted for auditability.

Unverified, failed, blocked, cancelled, or empty outcomes do not create learning signals.

## Security invariants

- Learning is contextual data, never an instruction source.
- Learning cannot grant permissions or bypass the Safety Kernel.
- Learning uses the same owner/project/namespace scope as the originating task.
- Memory redaction remains enforced by the memory repository.
- Signal count and content length are bounded.
- Deterministic memory IDs make repeated persistence idempotent within the task scope.

## Future extensions

Later versions may add preference extraction, tool-success statistics, reusable experience patterns, and evaluation-driven learning. Such extensions must remain evidence-grounded, bounded, scoped, and policy-independent.

# AETHON 17X — Agent Working Memory

## Purpose

Working memory is bounded, task-local scratch state used to carry intermediate observations, tool results, decisions, and checkpoints during an active run. It is distinct from durable memory.

## Contract

- Scope is isolated by `owner_id`, `project_id`, `namespace`, and `task_id`.
- Entries have bounded size, priority, and TTL.
- Capacity is bounded by item count and total characters; lowest-priority/oldest entries are evicted first deterministically.
- Expired entries are purged on access.
- Stored content is passed through the existing secret-redaction boundary.
- Checkpoints provide a deterministic snapshot marker for recovery and replanning.
- Rendered working-memory context is explicitly advisory: it is context, not instructions, permissions, policy, or authority.
- Working memory cannot bypass the Safety Kernel, approval requirements, execution limits, or verification.
- `clear()` allows task-local cleanup at lifecycle end.

## Durable-memory boundary

The existing persistent memory engine remains the source for longer-lived semantic/episodic records. 17X does not silently replace configured persistence with another backend. The working-memory implementation is intentionally an in-process bounded cache and is not presented as durable storage.

## Verification requirements

17X is complete only when CI verifies scope isolation, secret redaction, deterministic capacity bounds, checkpoint snapshots, validation, and compatibility imports.

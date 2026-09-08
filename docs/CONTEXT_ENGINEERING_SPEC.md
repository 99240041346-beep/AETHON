# AETHON 17Y — Context Engineering

## Purpose

17Y turns bounded task, memory, and tool observations into deterministic advisory context for reasoning. It is not an authorization or policy layer.

## Contract

- Context is ordered deterministically by priority, source, and content.
- Item count and total packet character count are hard bounded.
- Secrets are redacted before rendering.
- Untrusted instruction-like content is sanitized rather than promoted to authority.
- Task context is explicit and highest priority, but remains separate from Safety Kernel decisions.
- Memory records can be projected into context without changing durable-memory semantics.
- Truncation is explicit in `ContextPacket.truncated`.
- Safety Kernel, approvals, execution limits, and verification remain authoritative outside this context builder.

## Verification

CI must verify deterministic ordering, hard character bounds, truncation, secret redaction, instruction sanitization, validation, and memory projection.

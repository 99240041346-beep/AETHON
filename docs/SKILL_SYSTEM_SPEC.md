# AETHON Phase 24 — Skill System

Phase 24 provides a bounded registry and execution policy boundary for reusable skills.

## Guarantees

- Case-insensitive skill lookup with bounded metadata.
- Hard skill, request, input, and output budgets.
- Explicit approval for skills marked as requiring approval.
- Handler isolation: the policy layer does not execute arbitrary shell or network operations itself.
- Deterministic stop-on-failure behavior.
- Conservative planning that never invents a capability.

## Security boundary

Skill metadata, inputs, and handler outputs are untrusted. Skill registration does not grant authorization and cannot bypass Safety Kernel policy, approvals, execution limits, verification, or audit requirements.

Production integrations still require authenticated capability registration, owner/project isolation, lifecycle management, provenance/version policy, telemetry, and integration tests. This phase does not claim a marketplace or unrestricted plugin execution system.

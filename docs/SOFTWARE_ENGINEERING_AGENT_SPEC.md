# AETHON Phase 21 — Software Engineering Agent

This phase adds a bounded repository-engineering policy boundary. It supports validated read/write/delete/test/lint/diff request types through an adapter; the policy layer does not execute shell commands, mutate repositories, or fabricate tool results itself.

## Safety guarantees

- Operations have a hard count budget.
- Repository paths reject absolute paths, traversal, NUL bytes, and Windows separators.
- Write content has a hard size limit.
- Marked operations require explicit approval.
- A failed adapter operation stops the remaining operation sequence.
- Missing or untrusted provider adapters fail closed rather than being simulated.
- Planning is conservative and advisory.
- Adapter output is not authorization and cannot bypass the Safety Kernel, approvals, execution limits, verification, or audit requirements.

## Production boundary

A real implementation still requires a verified repository adapter/sandbox, patch application controls, command allowlists, test/lint execution isolation, secret handling, diff verification, and integration tests against the target execution environment. This module deliberately does not claim those provider-specific capabilities by itself.

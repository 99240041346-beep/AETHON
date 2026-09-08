# Phase 26 — Model Strategy / Router

AETHON model routing is a bounded, deterministic policy boundary.

## Guarantees
- Candidate count and metadata are bounded.
- Empty, duplicate, negative-cost, and negative-latency candidates are rejected.
- Requests require a non-empty task and validate cost/latency constraints.
- Required capabilities are matched before selection.
- Approval-required requests/candidates cannot route without explicit approval.
- Selection is deterministic: priority, then cost, latency, and name.
- Provider/network credentials and transport execution remain outside this module.

## Safety
Routing is advisory policy. A route does not grant authorization and cannot bypass the Safety Kernel, approvals, execution limits, verification, or audit requirements. Provider adapters must enforce their own authentication, timeouts, quotas, and failure handling.

# Phase 26 — Model Strategy / Router

AETHON routing is a deterministic, bounded, provider-neutral policy boundary.

## Guarantees
- Candidate count and metadata are bounded.
- Candidate names are non-empty and unique case-insensitively.
- Cost, latency, capability, and approval constraints are enforced before selection.
- Selection is deterministic: priority, then cost, latency, then name.
- Fallback occurs only among candidates allowed by the request constraints.
- Provider credentials, network calls, and transport execution remain outside this module.

## Safety
A route does not grant authorization. Routing cannot bypass the Safety Kernel, approvals, execution limits, verification, or audit requirements. Provider adapters must enforce authentication, timeouts, quotas, and failure handling.

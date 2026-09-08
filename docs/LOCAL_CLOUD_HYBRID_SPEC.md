# Phase 27 — Local / Cloud Hybrid Execution

AETHON uses a deterministic policy boundary to select between approved local and cloud execution candidates.

## Guarantees
- `LOCAL`, `CLOUD`, and `AUTO` request placement is explicit and bounded.
- Cost, latency, network, and approval constraints are hard eligibility filters.
- `AUTO` may select either location; explicit placement cannot silently fall back to the other location.
- Selection is deterministic by priority, cost, latency, then candidate name.
- Fallback occurs only among candidates already allowed by the request.
- This layer contains no provider credentials, network clients, subprocess execution, or transport adapters.

## Safety
A route does not authorize execution. The Safety Kernel, approvals, execution limits, verification, audit, and adapter-level authentication remain authoritative. Network/cloud execution requires explicit approval when requested or when a candidate is guarded.

# Phase 28 — Distributed AETHON

AETHON uses a bounded deterministic policy boundary to select an eligible distributed execution candidate.

## Guarantees
- Candidate count, capability metadata, load, cost, and latency are bounded.
- Candidate names are non-empty and unique case-insensitively.
- Capability, preferred-region, cost, and latency constraints are hard eligibility filters.
- Selection is deterministic by priority, load, cost, latency, then candidate name.
- Guarded candidates and approval-required requests fail closed without approval.
- Missing eligible candidates fail closed; this module never simulates remote execution.
- Provider transports, credentials, leases, retries, and worker execution remain outside this policy boundary.

## Safety
A route does not authorize execution. The Safety Kernel, authorization, approvals, execution limits, verification, and audit remain authoritative. A concrete distributed adapter must authenticate its worker, enforce timeouts/quotas, verify results, and report failures without bypassing these controls.

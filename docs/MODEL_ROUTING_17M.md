# AETHON 17M — Intelligent Model Routing

The routing layer classifies task complexity, matches required capabilities, prefers healthy low-cost/low-latency candidates, and falls back within a strict attempt budget.

## Guarantees

- deterministic classification and ranking
- capability-gated model selection
- provider health checks before selection/execution
- maximum five generation attempts
- fallback telemetry and latency measurement
- no secret values are placed in routing telemetry

Routing never grants tools or permissions. Tool authorization remains owned by the SafetyKernel.

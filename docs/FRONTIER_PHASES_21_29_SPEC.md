# AETHON Phases 21-29 — Frontier Capability Foundation

This release establishes one bounded, provider-neutral contract for the remaining roadmap capabilities:

- **21 Software Engineering Agent** — software-engineering operations through an adapter boundary.
- **22 Voice** — speech operations through an adapter boundary.
- **23 Real-Time** — streaming/realtime operations through an adapter boundary.
- **24 Skill System** — bounded deterministic skill metadata registry.
- **25 Evaluation Lab** — deterministic evaluation cases and scoring.
- **26 Model Strategy/Router** — model-routing requests through the same policy boundary.
- **27 Local/Cloud Hybrid** — local/cloud execution adapters behind policy.
- **28 Distributed AETHON** — distributed capability adapters behind policy.
- **29 IoT/Physical Gateway** — physical-world operations require explicit approval when marked.

## Guarantees

- Global operation, payload-item, and payload-text limits.
- Explicit approval gate for marked operations.
- Provider-specific execution is isolated behind adapters.
- Execution stops deterministically after a failed operation.
- Evaluation is deterministic and bounded.
- Skill registration is metadata only and does not grant authority.
- Missing adapters fail closed rather than being simulated.
- These capabilities cannot bypass the Safety Kernel, authorization, execution limits, verification, or audit requirements.

## Important scope boundary

This is the complete **foundation contract** for phases 21-29, not a claim that OS automation, speech synthesis/recognition, realtime transport, model-provider APIs, distributed workers, or physical IoT drivers have been magically implemented. Concrete providers must be integrated and verified behind these contracts before those capabilities are production-complete.

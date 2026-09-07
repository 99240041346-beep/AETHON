# AETHON Research Verification

Step 17H adds a bounded verification layer for autonomous research.

## Contract

`claims + source evidence -> supported | disputed | unsupported + provenance`

## Guarantees

- claim evaluation is deterministic and bounded
- only HTTP(S) evidence is eligible
- disputed claims are never silently promoted to supported results
- unsupported claims remain explicitly unresolved
- source identifiers are preserved for provenance
- source text is treated as untrusted data, never executable instructions

This verifier does not perform external side effects. Any action derived from research must pass the normal AgentBrain and SafetyKernel controls.

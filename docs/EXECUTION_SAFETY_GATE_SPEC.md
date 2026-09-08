# Execution Safety Gate

The execution safety gate is the narrow boundary between a capability adapter and actual execution authorization.

## Contract

- Every adapter execution must be evaluated by the authoritative `SafetyKernel`.
- `CRITICAL` operations are denied even when an approval flag is supplied.
- `MEDIUM`, `HIGH`, and side-effecting operations require an explicit approval signal.
- Approval is an input to the gate, not something inferred from planning, memory, model output, or experience.
- The gate never executes tools and never grants permissions beyond the SafetyKernel decision.
- A blocked request fails closed.

## Integration rule

Runtime/tool adapters should call `ExecutionGuard.evaluate(...)` immediately before execution and treat any `ExecutionGuardError` as a hard stop. The adapter remains responsible for its own timeout, argument validation, result handling, and verification.

The existing SafetyKernel remains authoritative; this component is a fail-closed adapter boundary, not a replacement policy engine.

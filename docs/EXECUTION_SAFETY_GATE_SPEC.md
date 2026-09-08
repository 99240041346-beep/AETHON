# Execution Safety Gate

AETHON preserves the existing distributed `ExecutionGuard` completion/lease fencing contract and adds a separate `SafetyExecutionGate` for authorization immediately before tool execution.

## Contract
- The authoritative `SafetyKernel` is evaluated for every gated operation.
- `CRITICAL` is denied even when approval is supplied.
- `MEDIUM`, `HIGH`, and side-effecting operations require explicit approval.
- Approval is never inferred from planning, memory, model output, or experience.
- `effective_decision` is `ALLOW` only after the SafetyKernel permits the operation and any required explicit approval is present.
- The gate never executes a tool.
- Blocked operations fail closed.

The existing distributed completion/failure guard remains unchanged and continues to enforce worker lease fencing and idempotent task completion.

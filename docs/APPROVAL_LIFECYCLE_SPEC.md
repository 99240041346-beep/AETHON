# Explicit Approval Lifecycle

AETHON treats approval as an explicit, scoped authorization transition.

## Contract

1. A safety decision may require approval.
2. The runtime records the exact task, plan step, tool, risk, and side-effecting operation awaiting approval.
3. Approval must name an explicit approver.
4. Approval is scoped to the exact `(task_id, step_id, tool)` tuple.
5. A different tool or step cannot consume that approval.
6. Approval is single-use: successful consumption removes the authorization.
7. Missing, stale, ambiguous, or mismatched approval fails closed.
8. Approval state never executes a tool itself.
9. SafetyKernel remains authoritative: an approval lifecycle cannot turn a DENY decision into ALLOW.
10. Memory, planning, model output, experience, or strategy selection cannot be treated as approval.

## Runtime integration requirement

The lifecycle component is intentionally execution-neutral. `AgentRuntime` must use it at the safety boundary so an `APPROVAL_REQUIRED` result checkpoints `AWAITING_APPROVAL` and returns without entering generic failure/replanning. A later explicit approval must restore the same pending plan step and allow exactly that authorized tool execution, subject to a fresh SafetyKernel decision.

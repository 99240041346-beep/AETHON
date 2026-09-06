# AETHON Initial Architecture

## System

```text
User
  ↓
Web UI
  ↓
API Gateway
  ↓
Orchestrator
  ├── Goal understanding
  ├── Task state
  └── Planner
       ↓
Model Router
       ↓
Agent Runtime
  ├── Tool Registry
  ├── Memory
  ├── Execution
  └── Recovery
       ↓
Safety Kernel
  ├── Identity
  ├── Authorization
  ├── Risk analysis
  ├── Policy
  ├── Approval
  └── Audit
       ↓
Authorized Tool
       ↓
Observation
       ↓
Verification
       ↓
Task result / Memory
```

## AETHON-0 service boundaries

### `apps/web`
User-facing application. It should not contain model credentials or privileged execution logic.

### `services/api`
HTTP API, authentication boundary, request validation, and API-level authorization.

### `services/orchestrator`
Converts goals into task state and coordinates planning/execution. It must not bypass the safety layer.

### `services/memory`
Project and user-approved memory retrieval/storage. Memory operations require access control and provenance.

### `services/evaluation`
Runs deterministic and model-assisted evaluations and records versioned results.

### `packages/tools`
Common tool contracts, schemas, permission metadata, and tool implementations/adapters.

### `packages/security`
Shared authorization, risk classifications, policy decisions, secret-handling interfaces, and audit contracts.

### `packages/schemas`
Typed API and internal data contracts.

## Execution state

Tasks should have explicit states rather than relying on unstructured conversation text:

`QUEUED → PLANNING → AWAITING_APPROVAL → EXECUTING → VERIFYING → SUCCEEDED`

Failure paths include `FAILED`, `CANCELLED`, `BLOCKED`, and `REPLANNING`.

## Design rules

1. Model output is untrusted input.
2. Tools are capability boundaries.
3. Every side-effecting tool declares permissions and risk.
4. Execution must be cancellable and time-bounded.
5. Results must be observable and auditable.
6. Verification is separate from generation whenever practical.
7. Provider-specific model code stays behind a model-router interface.
8. External credentials are never placed in prompts.
9. User data is isolated by account/project.
10. New infrastructure requires a documented reason.

# AETHON Technical Architecture Specification

**Milestone:** 0.2 — Technical Architecture Specification  
**Status:** Draft baseline for AETHON-0

## 1. Design Goal

AETHON-0 is a provider-agnostic, tool-using agent runtime. The runtime must make task state, permissions, tool calls, observations, verification, and failures explicit and auditable.

The architecture separates:

- intelligence from execution
- planning from authorization
- tool selection from tool implementation
- generation from verification
- transient state from durable memory
- user intent from privileged actions

## 2. Core Task Contract

Every user request becomes a `Task`.

```text
Task
├── id
├── tenant_id
├── user_id
├── project_id?
├── goal
├── constraints[]
├── context{}
├── requested_capabilities[]
├── status
├── priority
├── created_at
├── updated_at
└── deadline?
```

### Task statuses

```text
QUEUED
PLANNING
AWAITING_APPROVAL
EXECUTING
VERIFYING
REPLANNING
SUCCEEDED
FAILED
BLOCKED
CANCELLED
```

A task transition must be recorded as an event. Invalid transitions are rejected by the orchestrator.

## 3. Agent Runtime Contract

The agent runtime implements:

```text
receive(task)
  → load_context()
  → plan()
  → authorize_actions()
  → execute_step()
  → observe()
  → verify()
  → continue | replan | ask | block | finish
```

The runtime must support cancellation, timeouts, bounded retries, and recovery from tool failures.

A model response is never treated as an authorized action by itself.

## 4. Plan Contract

A plan is a sequence of typed steps:

```text
Plan
├── id
├── task_id
├── version
├── objective
├── steps[]
└── assumptions[]

PlanStep
├── id
├── order
├── intent
├── tool_id?
├── input{}
├── expected_observation
├── risk_class
├── requires_approval
└── status
```

Plans are disposable execution artifacts. The system may replace a plan when observations invalidate assumptions.

## 5. Tool Interface

Every tool exposes metadata before execution:

```text
Tool
├── id
├── version
├── name
├── description
├── input_schema
├── output_schema
├── permissions[]
├── risk_class
├── supports_dry_run
├── timeout_ms
├── network_policy
└── filesystem_policy
```

Execution contract:

```text
ToolRequest
├── request_id
├── task_id
├── tool_id
├── input
├── actor
├── authorization_context
└── idempotency_key?
```

```text
ToolResult
├── request_id
├── status
├── output
├── observations[]
├── error?
├── duration_ms
└── side_effects[]
```

Initial AETHON-0 tools should be narrow and testable: calculator, controlled web search, file operations inside an approved workspace, and sandboxed code execution.

## 6. Risk Classes

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Risk is evaluated from the action and context, not merely from the model's requested label.

High-impact or irreversible actions require explicit authorization according to policy. The model cannot grant itself permission.

## 7. Model Router Contract

The orchestrator calls a provider-neutral model router:

```text
ModelRequest
├── task_type
├── messages/context
├── required_capabilities[]
├── max_latency_ms?
├── max_cost?
├── privacy_class
├── tool_support_required
└── output_schema?
```

```text
ModelResponse
├── provider
├── model
├── output
├── tool_intents[]
├── usage
├── latency_ms
└── finish_reason
```

The router may choose among configured providers/models using capability, reliability, latency, cost, privacy, and tool compatibility. No application layer should depend directly on one model vendor.

## 8. Memory Interface

Memory is divided into:

- working memory — current task context
- episodic memory — prior task events/outcomes
- semantic memory — durable facts/knowledge
- project memory — project-scoped information
- preference memory — user-approved preferences

Base interface:

```text
remember(item, scope, metadata)
retrieve(query, scope, filters, limit)
update(memory_id, patch)
delete(memory_id)
```

Memory writes must carry provenance and scope. Sensitive information must not be persisted merely because a model generated it.

## 9. Verification Contract

Verification is independent from generation.

```text
VerificationRequest
├── task_id
├── expected_result
├── actual_result
├── evidence[]
└── verification_rules[]
```

```text
VerificationResult
├── passed
├── confidence
├── checks[]
├── discrepancies[]
└── recommended_action
```

Recommended actions:

```text
ACCEPT
RETRY
REPLAN
ASK_USER
BLOCK
```

## 10. Security Policy Interface

Authorization occurs before privileged execution:

```text
authorize(actor, action, resource, context)
  → ALLOW | APPROVAL_REQUIRED | DENY
```

The policy engine evaluates identity, scope, permission, risk, resource, reversibility, and current task context.

Security controls include least privilege, credential isolation, sandboxing, resource limits, secret redaction, audit logging, cancellation, and tenant/project isolation.

## 11. API Boundary

AETHON-0 API resources:

```text
POST   /v1/tasks
GET    /v1/tasks/{task_id}
POST   /v1/tasks/{task_id}/cancel
GET    /v1/tasks/{task_id}/events
POST   /v1/tasks/{task_id}/approval
GET    /v1/tools
POST   /v1/memory/search
GET    /health
GET    /ready
```

The external API must validate all input, authenticate users, enforce authorization, return structured errors, and attach correlation/request IDs.

## 12. Event Model

Important runtime events include:

```text
task.created
task.status_changed
plan.created
plan.replaced
model.requested
model.completed
tool.requested
tool.started
tool.completed
tool.failed
approval.requested
approval.granted
approval.denied
verification.completed
memory.written
security.blocked
task.completed
task.failed
```

Events form the basis of observability, auditability, replay/debugging, and evaluation.

## 13. Persistence Strategy

Initial production-oriented direction:

- PostgreSQL for durable application state
- pgvector for semantic memory when needed
- Redis only for transient queues/cache/coordination when justified
- object storage for large artifacts

The first implementation should avoid adding infrastructure that is not required by the current milestone.

## 14. Repository Mapping

```text
apps/web                 User interface
services/api             HTTP/API boundary
services/orchestrator    Task lifecycle and planning
services/memory          Memory operations
services/inference       Model provider abstraction/router
services/evaluation      Benchmarks and scoring
packages/tools           Tool contracts and implementations
packages/security        Policy, authorization, audit contracts
packages/schemas         Shared typed schemas
packages/shared          Common utilities
```

## 15. Observability

Every task, model call, tool call, security decision, and verification step should be traceable through a correlation ID.

Minimum telemetry:

- request/task latency
- model latency and token usage
- tool success/failure rate
- retry count
- verification outcome
- security decision
- task completion status
- estimated cost

## 16. Failure Semantics

AETHON must distinguish:

- invalid user input
- model failure
- tool failure
- authorization denial
- timeout
- cancellation
- verification failure
- unavailable dependency
- policy block

Retries must be bounded and must not repeat non-idempotent side effects without explicit protection.

## 17. Definition of Done for Milestone 0.2

The architecture milestone is complete when:

1. Task, plan, tool, model, memory, verification, security, and event contracts are documented.
2. Service boundaries are explicit.
3. Privileged actions require policy evaluation.
4. Provider-specific model code is isolated behind an interface.
5. Runtime states and failure semantics are explicit.
6. The contracts are implementable as typed schemas in Phase 1.

## 18. Next Implementation Milestone

**Phase 1 — AETHON-0 Foundation**

Implement the smallest end-to-end vertical slice:

```text
Web/API request
→ Task creation
→ Orchestrator
→ Model router
→ Tool selection
→ Policy check
→ Tool execution
→ Verification
→ Task result
→ Audit/event record
```

Only after this path passes automated tests should additional tools, browser control, computer control, persistent memory, or multimodal capabilities be added.

# AETHON Technical Architecture Specification

**Milestone:** 0.2 — Technical Architecture Specification  
**Status:** Draft baseline for AETHON-0

## 1. Design Goal

AETHON-0 is a provider-agnostic, tool-using agent runtime. The runtime must make task state, permissions, tool calls, observations, verification, failures, and scheduling explicit and auditable.

The architecture separates:

- intelligence from execution
- planning from authorization
- tool selection from tool implementation
- generation from verification
- transient state from durable memory
- user intent from privileged actions
- task admission from task execution

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
PAUSED
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
  → continue | replan | ask | pause | block | finish
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

## 11. Scheduler Contract

AETHON-0 uses a bounded in-process scheduler as its first concurrency implementation:

```text
Task request
    ↓
Priority + dependency admission
    ↓
Resource quotas
    ↓
N bounded workers
 ┌──────┬──────┬──────┐
Agent  Agent  Agent  ...
 └──────┴──────┴──────┘
    ↓
Durable task/agent checkpoints
```

Rules:

- lower numeric priority executes first
- equal priority is FIFO among eligible tasks
- tasks may depend on previously submitted scheduler futures
- a dependent task cannot start until all dependencies succeed
- independent ready work can bypass a blocked dependency
- resource requests are admitted only when the configured quota is available
- a request exceeding a declared quota is rejected at admission
- `AETHON_MAX_CONCURRENT_TASKS` caps active workers
- scheduler admission never bypasses Safety Kernel authorization
- worker failures propagate to the task's normal recovery path

The current implementation intentionally uses a bounded thread pool rather than introducing Redis/Kubernetes before the workload requires distributed coordination. The dependency and resource interfaces are designed to survive a later move to a durable distributed queue.

## 12. API Boundary

AETHON-0 API resources:

```text
POST   /v1/tasks
GET    /v1/tasks/{task_id}
POST   /v1/tasks/{task_id}/cancel
POST   /v1/tasks/{task_id}/pause
POST   /v1/tasks/{task_id}/resume
GET    /v1/tasks/{task_id}/events
GET    /v1/tasks/{task_id}/plan
GET    /v1/tasks/{task_id}/audit
GET    /v1/scheduler
GET    /v1/tools
POST   /v1/memory/search
GET    /health
GET    /ready
```

The external API must validate all input, authenticate users, enforce authorization, return structured errors, and attach correlation/request IDs.

## 13. Event Model

Important runtime events include:

```text
task.created
task.queued
task.state_changed
task.paused
task.pause_requested
plan.created
plan.replaced
plan.replanned
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
task.completed
task.failed
task.blocked
```

Events form the basis of observability, auditability, replay/debugging, and evaluation.

## 14. Persistence Strategy

Initial production-oriented direction:

- PostgreSQL for durable application state
- pgvector for semantic memory when needed
- Redis only for transient queues/cache/coordination when justified
- object storage for large artifacts

The current AETHON-0 scheduler is intentionally local and bounded. A later distributed scheduler can preserve the same task/checkpoint contracts while moving queue ownership, dependency state, resource leases, and worker heartbeats into durable infrastructure.

## 15. Repository Mapping

```text
apps/web                 User interface
services/api             HTTP/API boundary and AETHON-0 scheduler
services/orchestrator    Task lifecycle and planning
services/memory          Memory operations
services/inference       Model provider abstraction/router
services/evaluation      Benchmarks and scoring
packages/tools           Tool contracts and implementations
packages/security        Policy, authorization, audit contracts
packages/schemas         Shared typed schemas
packages/shared          Common utilities
```

## 16. Observability

Every task, model call, tool call, security decision, scheduler admission, and verification step should be traceable through a correlation ID.

Minimum telemetry:

- request/task latency
- queued time and execution time
- active/queued worker counts
- model latency and token usage
- tool success/failure rate
- retry count
- verification outcome
- security decision
- task completion status
- estimated cost

## 17. Failure Semantics

AETHON must distinguish:

- invalid user input
- model failure
- tool failure
- authorization denial
- timeout
- cancellation
- pause
- verification failure
- unavailable dependency
- policy block
- scheduler shutdown/admission failure
- dependency failure
- resource quota exhaustion

Retries must be bounded and must not repeat non-idempotent side effects without explicit protection.

## 18. Definition of Done for Milestone 0.2

The architecture milestone is complete when:

1. Task, plan, tool, model, memory, verification, security, event, and scheduler contracts are documented.
2. Service boundaries are explicit.
3. Privileged actions require policy evaluation.
4. Provider-specific model code is isolated behind an interface.
5. Runtime states and failure semantics are explicit.
6. The contracts are implementable as typed schemas in Phase 1.

## 19. Next Implementation Milestone

**Phase 1 — AETHON-0 Foundation**

Implement the smallest end-to-end vertical slice:

```text
Web/API request
→ Task creation
→ Scheduler
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

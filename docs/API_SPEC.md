# AETHON API Specification

## Scope

AETHON-0 exposes a small versioned HTTP API. The API is an authentication and authorization boundary; clients never receive direct access to privileged tools.

## Conventions

- Base path: `/v1`
- JSON request/response bodies
- ISO-8601 UTC timestamps
- Every response should include `request_id`
- Authentication and project authorization are required for non-health endpoints
- Errors use a stable shape

## Error Contract

```json
{
  "error": {
    "code": "TASK_NOT_FOUND",
    "message": "Task was not found",
    "details": {}
  },
  "request_id": "..."
}
```

## Endpoints

### `GET /health`

Liveness check. Must not require authentication.

### `GET /ready`

Readiness check. Reports whether required application dependencies are available.

### `POST /v1/tasks`

Create a task.

Request:

```json
{
  "goal": "string",
  "project_id": "string",
  "constraints": [],
  "requested_capabilities": [],
  "priority": "normal"
}
```

Response: `201` with the canonical task representation.

### `GET /v1/tasks/{task_id}`

Returns task state, current plan summary, result/error, and timestamps. The caller must have access to the task's project.

### `POST /v1/tasks/{task_id}/cancel`

Requests cancellation. Cancellation is idempotent.

### `POST /v1/tasks/{task_id}/approval`

Approve or deny a pending action.

```json
{
  "decision": "approve",
  "scope": "single_action"
}
```

The server must verify that the caller is authorized to approve the specific action.

### `GET /v1/tasks/{task_id}/events`

Returns task lifecycle and audit-safe execution events in chronological order.

### `GET /v1/tools`

Returns tools visible to the authenticated project/user, including permission and risk metadata. Secrets and credentials are never returned.

### `POST /v1/memory`

Creates or replaces a memory record inside the explicitly supplied project/namespace scope. Content is validated and secrets are redacted before storage.

```json
{
  "memory_id": "string",
  "content": "string",
  "project_id": "string",
  "namespace": "project",
  "memory_type": "semantic",
  "source": "user",
  "confidence": 0.9,
  "expires_at": null
}
```

### `POST /v1/memory/search`

Searches only within the requested project and namespace. Results include provenance, confidence, and retention metadata.

```json
{
  "query": "string",
  "project_id": "string",
  "namespace": "project",
  "limit": 10
}
```

### `DELETE /v1/memory/{memory_id}`

Deletes a memory only when the supplied project and namespace match the stored record. A mismatched scope is treated as not found.

```json
{
  "project_id": "string",
  "namespace": "project"
}
```

## Agent Memory Integration

Before model reasoning, the task runtime retrieves at most five relevant records from the task's project namespace. Retrieved memory is explicitly passed as context, never as authority or executable instructions. After successful verification, the task result may be stored as episodic memory through the same redaction and scope controls.

## Idempotency

Task creation and side-effecting API operations should support an idempotency key. The server must not replay a non-idempotent operation solely because a client retried a request.

## Security Requirements

- Authenticate before protected resource access.
- Authorize every task/project/resource access.
- Validate and bound request sizes.
- Rate-limit expensive operations.
- Never accept a client-supplied permission escalation.
- Never expose model/provider credentials.
- Record security-relevant decisions.
- Treat memory as context, not authority.
- Enforce project and namespace isolation on every memory operation.

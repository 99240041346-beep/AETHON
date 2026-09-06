# AETHON API Specification

## Scope

AETHON-0 exposes a small versioned HTTP API. The API is an authentication and authorization boundary; clients never receive direct access to privileged tools.

## Conventions

- Base path: `/v1`
- JSON request/response bodies
- ISO-8601 UTC timestamps
- Every response should include `request_id` as the API matures
- Health endpoints are public; protected resources use bearer authentication when configured
- Errors use a stable shape

## Authentication

Configure `AETHON_API_TOKEN` and `AETHON_API_OWNER_ID` in production. Protected task and memory endpoints then require `Authorization: Bearer <token>`. The server derives the owner identity from the authenticated configuration; clients cannot select another owner by putting an arbitrary owner ID in the JSON body.

The current adapter is intentionally single-owner per configured token. A future OAuth/OIDC identity provider can replace it while retaining the `owner_id` ownership boundary.

## Endpoints

### `GET /health`

Liveness check. Does not require authentication.

### `GET /ready`

Readiness check. Reports the configured persistence mode.

### `POST /v1/tasks`

Create a task. The server assigns the authenticated owner identity.

### `GET /v1/tasks/{task_id}`

Returns task state only when the authenticated owner matches the task owner.

### `POST /v1/tasks/{task_id}/cancel`

Requests cancellation after owner authorization.

### `GET /v1/tasks/{task_id}/events`

Returns lifecycle and audit-safe events after owner authorization.

### `GET /v1/tools`

Returns visible tool metadata without credentials.

### `POST /v1/memory`

Creates or replaces a memory inside the authenticated owner's project/namespace scope. Secrets are redacted before persistence.

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

Searches only within the authenticated owner, project, and namespace. Results include provenance, confidence, and retention metadata.

### `DELETE /v1/memory/{memory_id}`

Deletes only when owner, project, and namespace match. A mismatched scope is treated as not found.

## Durable Persistence

When `AETHON_DATABASE_URL` is configured with PostgreSQL, memory is stored in the PostgreSQL `memories` table rather than the process-local engine. Apply `services/api/migrations/002_memory_ownership.sql` to upgrade existing databases before deployment. This prevents memory from disappearing when API workers restart.

## Agent Memory Integration

Before model reasoning, the runtime retrieves at most five relevant records from the task owner's project namespace. Retrieved memory is context only—not authority, permission, or executable instruction. After successful verification, the verified task result may be stored as episodic memory through the same owner, project, namespace, and secret-redaction controls.

## Security Requirements

- Authenticate before protected resource access.
- Authorize every task/project/resource access.
- Never accept a client-supplied owner identity as an authorization decision.
- Validate and bound request sizes.
- Rate-limit expensive operations.
- Never expose model/provider credentials.
- Treat memory as context, not authority.
- Enforce owner, project, and namespace isolation on every memory operation.
- Audit security-relevant decisions.

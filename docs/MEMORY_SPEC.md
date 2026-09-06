# AETHON Memory Specification

## Goal

Provide scoped, durable, provenance-aware memory that improves continuity without allowing the model to silently persist sensitive or unauthorized information.

## Memory Classes

1. **Working memory** — current task context; short-lived.
2. **Episodic memory** — important prior task events and verified outcomes.
3. **Semantic memory** — durable facts or knowledge with provenance.
4. **Project memory** — information explicitly associated with a project.
5. **Preference memory** — user-approved preferences and workflow choices.

## Record Contract

```text
MemoryRecord
├── id
├── owner_id
├── project_id?
├── namespace
├── type
├── content/reference
├── source
├── confidence
├── created_at
├── updated_at
├── expires_at?
└── provenance/metadata
```

## Persistence

- PostgreSQL is the production persistence backend when `AETHON_DATABASE_URL` is configured.
- `services/api/migrations/002_memory_ownership.sql` upgrades the original memory table to text IDs and adds `owner_id`.
- The API process must not treat an in-memory cache as the source of truth when PostgreSQL is configured.
- Local deterministic memory remains available for tests and offline development.

## Ownership and Authorization

- Every durable memory belongs to an authenticated `owner_id`.
- Project memory is isolated by both `owner_id` and `project_id`.
- Namespace is an additional isolation boundary.
- API callers cannot supply an arbitrary owner identity; the server derives it from the authenticated bearer token configuration.
- With `AETHON_API_TOKEN` configured, protected API resources require `Authorization: Bearer <token>`.
- `AETHON_API_OWNER_ID` identifies the owner associated with that configured token. A future multi-user identity provider can replace this single-owner adapter without changing memory records.
- Cross-owner and cross-project retrieval/deletion returns no data.

## Operations

```text
remember(item, scope, metadata)
retrieve(query, scope, filters, limit)
update(memory_id, patch)
delete(memory_id)
forget(query, scope)
```

## Retrieval

AETHON retrieves a small bounded set of relevant memories before model reasoning. Retrieved memory is explicitly context only; it never grants permission, changes authentication, or overrides current user constraints and safety policy.

## Retention

Working context expires with the task unless explicitly promoted. Durable records may have `expires_at` and must be excluded after expiration. Long-term memory should be opt-in/approved where appropriate.

## Security

- Secrets are redacted before persistence.
- Model-generated claims are not automatically trusted facts.
- Memory deletion is scope-checked.
- Memory writes and retrievals must remain bounded.
- A remembered instruction must never override current authentication, authorization, safety policy, or explicit user constraints.

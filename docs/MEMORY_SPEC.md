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
consolidate(scope)
analyze_conflicts(scope)
```

## Intelligent Retrieval

Retrieval uses a bounded hybrid score:

```text
score = 0.65 × lexical relevance
      + 0.15 × recency
      + 0.20 × confidence
```

Lexical relevance is deterministic and provider-independent. Recency uses a 30-day exponential decay. Confidence is supplied by the memory source and is never treated as proof of truth.

PostgreSQL retrieval first selects a bounded candidate set, then applies the same ranking model. This keeps the runtime behavior aligned between local development and production persistence.

Semantic/vector retrieval is an extension point for a future pgvector-backed embedding index. Embedding retrieval must remain scoped by owner, project, and namespace before similarity ranking is applied.

## Consolidation and Conflicts

Consolidation currently operates as a **review-only** operation: it reports duplicate content groups and explicit keyed conflicts without silently deleting or overwriting records. Automatic consolidation requires a higher-level policy and audit trail.

Explicit conflict keys use conservative `key: value` or `key=value` patterns. Conflicts are treated as uncertainty signals and must not be presented as established facts without resolution.

## Agent Integration

Before model reasoning, the runtime retrieves at most five relevant records from the task's authorized scope. The selected memory is injected as context only and is never executable authority. After successful verification, the task result may be persisted as episodic memory through the same ownership and redaction controls.

## Retention

Working context expires with the task unless explicitly promoted. Durable records may have `expires_at` and must be excluded after expiration. Long-term memory should be opt-in/approved where appropriate.

## Security

- Secrets are redacted before persistence.
- Model-generated claims are not automatically trusted facts.
- Memory deletion is scope-checked.
- Memory writes and retrievals must remain bounded.
- A remembered instruction must never override current authentication, authorization, safety policy, or explicit user constraints.

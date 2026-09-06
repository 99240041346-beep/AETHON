# AETHON Memory Specification

## Goal

Provide scoped, provenance-aware memory that improves continuity without allowing the model to silently persist sensitive or unauthorized information.

## Memory Classes

1. **Working memory** — current task context; short-lived.
2. **Episodic memory** — important prior task events and outcomes.
3. **Semantic memory** — durable facts or knowledge with provenance.
4. **Project memory** — information explicitly associated with a project.
5. **Preference memory** — user-approved preferences and workflow choices.

## Record Contract

```text
MemoryRecord
├── id
├── owner_type
├── owner_id
├── project_id?
├── type
├── content/reference
├── source
├── provenance
├── sensitivity
├── created_at
├── updated_at
├── retention_policy
└── embedding?
```

## Operations

```text
remember(item, scope, metadata)
retrieve(query, scope, filters, limit)
update(memory_id, patch)
delete(memory_id)
forget(query, scope)
```

## Access Rules

- Project memory is isolated by project.
- User memory is isolated by user.
- Retrieval must enforce authorization before returning records.
- A model cannot expand its own memory permissions.
- Cross-project retrieval is denied by default.
- Sensitive records require an explicit retention policy.
- Deletion/forget requests must be auditable.

## Provenance

Every durable record must identify where it came from, such as user input, verified tool output, imported document, or system-generated observation. Model-generated claims are not automatically trusted facts.

## Retrieval

AETHON-0 may begin with deterministic metadata/keyword retrieval. Semantic/vector retrieval can be added with PostgreSQL + pgvector when needed. Retrieval results should carry source and confidence/provenance metadata so the orchestrator can distinguish remembered information from current observations.

## Retention

Working context expires with the task unless explicitly promoted. Long-term memory is opt-in/approved where appropriate. The system must support deletion and retention enforcement.

## Safety

Memory is context, not authority. A remembered instruction must never override current authentication, authorization, safety policy, or explicit user constraints.

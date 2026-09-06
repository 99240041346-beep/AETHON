-- AETHON PostgreSQL canonical persistence schema.
-- Apply with a migration tool in production; this file is the initial reference schema.

CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY,
    goal TEXT NOT NULL,
    project_id TEXT,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 10),
    status TEXT NOT NULL,
    result_json JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS events (
    event_id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_task_created
    ON events(task_id, created_at);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(task_id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_task_created
    ON audit_log(task_id, created_at);

CREATE TABLE IF NOT EXISTS memories (
    memory_id UUID PRIMARY KEY,
    project_id TEXT,
    namespace TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memories_project_namespace
    ON memories(project_id, namespace);

-- AETHON initial PostgreSQL persistence schema.
-- Migration runner applies files in numeric order.

CREATE TABLE IF NOT EXISTS tasks (
    task_id UUID PRIMARY KEY,
    goal TEXT NOT NULL,
    project_id TEXT,
    owner_id TEXT NOT NULL DEFAULT 'local-dev',
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
CREATE INDEX IF NOT EXISTS idx_events_task_created ON events(task_id, created_at);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(task_id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'recorded',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_task_created ON audit_log(task_id, created_at);

CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL DEFAULT 'local-dev',
    project_id TEXT,
    namespace TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK (confidence BETWEEN 0 AND 1),
    source TEXT NOT NULL DEFAULT 'agent',
    memory_type TEXT NOT NULL DEFAULT 'semantic',
    expires_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memories_owner_project_namespace ON memories(owner_id, project_id, namespace);
CREATE INDEX IF NOT EXISTS idx_memories_namespace_type ON memories(namespace, memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at);

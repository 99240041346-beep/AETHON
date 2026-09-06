BEGIN;

-- Existing deployments may have UUID memory IDs from the initial schema.
ALTER TABLE memories ALTER COLUMN memory_id TYPE TEXT USING memory_id::text;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS owner_id TEXT NOT NULL DEFAULT 'local-dev';

CREATE INDEX IF NOT EXISTS idx_memories_owner_project_namespace
    ON memories(owner_id, project_id, namespace);

COMMIT;

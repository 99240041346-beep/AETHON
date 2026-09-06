-- Step 14H: shared PostgreSQL worker leases for multi-worker recovery.
-- Apply this migration before enabling distributed workers.

CREATE TABLE IF NOT EXISTS worker_leases (
    task_id UUID PRIMARY KEY REFERENCES tasks(task_id) ON DELETE CASCADE,
    worker_id TEXT NOT NULL,
    lease_token TEXT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_worker_leases_expires_at
    ON worker_leases(expires_at);

CREATE INDEX IF NOT EXISTS idx_tasks_recovery
    ON tasks(status, priority, created_at);

COMMENT ON TABLE worker_leases IS
    'Shared worker ownership leases used to prevent duplicate task execution and recover abandoned work.';

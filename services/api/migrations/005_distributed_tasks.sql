-- Step 16: shared PostgreSQL task persistence.
-- Apply after the canonical task/event schema.

CREATE INDEX IF NOT EXISTS idx_tasks_queue
    ON tasks(status, priority, created_at);

CREATE INDEX IF NOT EXISTS idx_tasks_owner_status
    ON tasks(owner_id, status, updated_at);

CREATE INDEX IF NOT EXISTS idx_events_task_created
    ON events(task_id, created_at);

CREATE INDEX IF NOT EXISTS idx_worker_leases_task_expiry
    ON worker_leases(task_id, expires_at);

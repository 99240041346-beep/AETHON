ALTER TABLE assistant_sessions
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_assistant_sessions_owner_updated
    ON assistant_sessions(owner_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_assistant_sessions_owner_archived
    ON assistant_sessions(owner_id, archived_at);

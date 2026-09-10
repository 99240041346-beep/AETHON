-- Persisted assistant conversation and device-action lifecycle.
-- Keeps conversational state separate from authorization state.

CREATE TABLE IF NOT EXISTS assistant_sessions (
    session_id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    project_id TEXT,
    language TEXT NOT NULL DEFAULT 'te-IN',
    title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assistant_sessions_owner_updated
    ON assistant_sessions(owner_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS assistant_messages (
    message_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES assistant_sessions(session_id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'te-IN',
    intent TEXT,
    action TEXT,
    status TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assistant_messages_session_created
    ON assistant_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_assistant_messages_owner_created
    ON assistant_messages(owner_id, created_at DESC);

CREATE TABLE IF NOT EXISTS device_commands (
    command_id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    arguments JSONB NOT NULL DEFAULT '{}'::jsonb,
    nonce TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('ACCEPTED', 'COMPLETED', 'REJECTED')),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_device_commands_owner_created
    ON device_commands(owner_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_commands_device_created
    ON device_commands(device_id, issued_at DESC);

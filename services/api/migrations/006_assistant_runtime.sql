-- AETHON assistant runtime persistence.
-- Keeps conversation state, device identity, and command receipts durable and owner-isolated.

CREATE TABLE IF NOT EXISTS assistant_sessions (
    session_id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    project_id TEXT,
    title TEXT,
    language TEXT NOT NULL DEFAULT 'te-IN',
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
    intent_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_assistant_messages_session_created
    ON assistant_messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_assistant_messages_owner_created
    ON assistant_messages(owner_id, created_at);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    device_type TEXT NOT NULL,
    display_name TEXT,
    platform TEXT,
    platform_version TEXT,
    status TEXT NOT NULL DEFAULT 'OFFLINE',
    capabilities_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_devices_owner_status ON devices(owner_id, status);

CREATE TABLE IF NOT EXISTS device_commands (
    command_id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    device_id TEXT NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    capability TEXT NOT NULL,
    arguments_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    nonce TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('ACCEPTED', 'COMPLETED', 'REJECTED', 'EXPIRED')),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    error TEXT,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_device_commands_owner_created
    ON device_commands(owner_id, issued_at DESC);
CREATE INDEX IF NOT EXISTS idx_device_commands_device_created
    ON device_commands(device_id, issued_at DESC);

CREATE TABLE IF NOT EXISTS tool_executions (
    execution_id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    task_id UUID REFERENCES tasks(task_id) ON DELETE SET NULL,
    tool_name TEXT NOT NULL,
    arguments_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    outcome TEXT NOT NULL CHECK (outcome IN ('ALLOWED', 'BLOCKED', 'SUCCEEDED', 'FAILED')),
    verification_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tool_executions_owner_created
    ON tool_executions(owner_id, created_at DESC);

-- Durable Android device registry and replay state.
-- Tokens are stored only as SHA-256 hashes; plaintext tokens are returned once at registration.
CREATE TABLE IF NOT EXISTS device_registry (
    device_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    token_hash TEXT NOT NULL,
    registration_nonce TEXT NOT NULL UNIQUE,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_registry_owner ON device_registry(owner_id);
CREATE INDEX IF NOT EXISTS idx_device_registry_heartbeat ON device_registry(last_seen);

CREATE TABLE IF NOT EXISTS device_replay_nonces (
    nonce TEXT PRIMARY KEY,
    device_id TEXT NOT NULL REFERENCES device_registry(device_id) ON DELETE CASCADE,
    command_id TEXT NOT NULL,
    used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_device_replay_device ON device_replay_nonces(device_id, used_at);

-- Durable Android command transport lifecycle.
-- Extends the existing command receipt table without widening capability policy.

ALTER TABLE device_commands DROP CONSTRAINT IF EXISTS device_commands_status_check;
ALTER TABLE device_commands ADD CONSTRAINT device_commands_status_check
    CHECK (status IN ('ACCEPTED', 'COMPLETED', 'REJECTED', 'EXPIRED', 'CANCELLED'));

ALTER TABLE device_commands ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMPTZ;
ALTER TABLE device_commands ADD COLUMN IF NOT EXISTS result_json JSONB;
ALTER TABLE device_commands ADD COLUMN IF NOT EXISTS verification_json JSONB;
ALTER TABLE device_commands ADD COLUMN IF NOT EXISTS result_received_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_device_commands_pending
    ON device_commands(device_id, expires_at, issued_at)
    WHERE status = 'ACCEPTED';
CREATE INDEX IF NOT EXISTS idx_device_commands_nonce
    ON device_commands(nonce);

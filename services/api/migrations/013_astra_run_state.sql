-- ASTRA production run/audit state extension. Idempotent for existing deployments.
CREATE TABLE IF NOT EXISTS astra_runs (
    run_id UUID PRIMARY KEY,
    owner_id TEXT NOT NULL,
    agent_id TEXT,
    status TEXT NOT NULL,
    goal TEXT NOT NULL,
    checkpoint_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_astra_runs_owner_status ON astra_runs(owner_id, status);
CREATE INDEX IF NOT EXISTS idx_astra_runs_updated ON astra_runs(updated_at);

CREATE TABLE IF NOT EXISTS astra_action_audit (
    audit_id UUID PRIMARY KEY,
    run_id UUID REFERENCES astra_runs(run_id) ON DELETE SET NULL,
    owner_id TEXT NOT NULL,
    action TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    outcome TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_astra_action_audit_owner_created ON astra_action_audit(owner_id, created_at);

from pathlib import Path


MIGRATION = Path(__file__).resolve().parents[1] / "migrations" / "006_assistant_runtime.sql"


def test_assistant_runtime_migration_exists_and_is_owner_isolated():
    sql = MIGRATION.read_text(encoding="utf-8")
    for table in (
        "assistant_sessions",
        "assistant_messages",
        "devices",
        "device_commands",
        "tool_executions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        assert "owner_id TEXT NOT NULL" in sql


def test_command_nonce_is_unique_and_commands_are_verifiable():
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "nonce TEXT NOT NULL UNIQUE" in sql
    assert "verified BOOLEAN NOT NULL DEFAULT FALSE" in sql
    assert "expires_at TIMESTAMPTZ NOT NULL" in sql
    assert "CHECK (status IN ('ACCEPTED', 'COMPLETED', 'REJECTED', 'EXPIRED'))" in sql

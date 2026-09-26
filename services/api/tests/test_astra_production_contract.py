from pathlib import Path


def test_astra_run_migration_contains_durable_state_and_audit():
    sql = (Path(__file__).parents[1] / "migrations" / "013_astra_run_state.sql").read_text()
    assert "astra_runs" in sql
    assert "checkpoint_json" in sql
    assert "astra_action_audit" in sql
    assert "approved BOOLEAN" in sql

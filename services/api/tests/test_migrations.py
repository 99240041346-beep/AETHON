import os

import pytest

from aethon.migrations import MigrationRunner


pytestmark = pytest.mark.integration


def test_migrations_apply_from_empty_database_and_are_idempotent():
    url = os.getenv("AETHON_DATABASE_URL")
    if not url:
        pytest.skip("AETHON_DATABASE_URL is not configured")

    runner = MigrationRunner(url)
    first = runner.migrate()
    second = runner.migrate()

    assert first
    assert first == sorted(first)
    assert second == []

    with __import__("psycopg").connect(url) as conn:
        rows = conn.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        ).fetchall()
        assert [row[0] for row in rows] == [runner._version(p) for p in runner.migrations()]

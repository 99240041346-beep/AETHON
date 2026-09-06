import os

import pytest

from aethon.postgres_pool import PostgreSQLPool


pytestmark = pytest.mark.integration


def test_pool_and_transaction_contract():
    url = os.getenv("AETHON_DATABASE_URL")
    if not url:
        pytest.skip("AETHON_DATABASE_URL is not configured")

    pool = PostgreSQLPool(url, min_size=1, max_size=2)
    try:
        assert pool.ping()
        with pool.transaction() as conn:
            conn.execute("CREATE TEMP TABLE aethon_pool_probe(value INTEGER)")
            conn.execute("INSERT INTO aethon_pool_probe(value) VALUES (42)")
            assert conn.execute("SELECT value FROM aethon_pool_probe").fetchone()[0] == 42
    finally:
        pool.close()

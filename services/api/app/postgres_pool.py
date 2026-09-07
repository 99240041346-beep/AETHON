from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from psycopg_pool import ConnectionPool


class PostgreSQLPool:
    """Bounded PostgreSQL connection pool with explicit transaction boundaries."""

    def __init__(self, database_url: str, *, min_size: int | None = None, max_size: int | None = None):
        self.database_url = database_url
        self.min_size = min_size or int(os.getenv("AETHON_DB_POOL_MIN", "1"))
        self.max_size = max_size or int(os.getenv("AETHON_DB_POOL_MAX", "10"))
        if self.min_size < 0 or self.max_size < 1 or self.min_size > self.max_size:
            raise ValueError("invalid PostgreSQL pool bounds")
        self.pool = ConnectionPool(
            conninfo=database_url,
            min_size=self.min_size,
            max_size=self.max_size,
            open=False,
        )
        self.pool.open(wait=True)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        with self.pool.connection() as conn:
            yield conn

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        with self.pool.connection() as conn:
            with conn.transaction():
                yield conn

    def ping(self) -> bool:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone()[0] == 1

    def close(self) -> None:
        self.pool.close()

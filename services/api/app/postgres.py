from __future__ import annotations

import os
from typing import Any

from aethon.postgres_pool import PostgreSQLPool


class PostgresStoreUnavailable(RuntimeError):
    """Raised when PostgreSQL persistence is requested but is not configured."""


class PostgresStore:
    """Pooled PostgreSQL adapter with explicit transaction support."""

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("AETHON_DATABASE_URL")
        if not self.database_url:
            raise PostgresStoreUnavailable("AETHON_DATABASE_URL is not configured")
        if not self.database_url.startswith(("postgres://", "postgresql://")):
            raise PostgresStoreUnavailable("AETHON_DATABASE_URL must be a PostgreSQL URL")
        try:
            self.pool = PostgreSQLPool(self.database_url)
        except Exception as exc:
            raise PostgresStoreUnavailable(f"PostgreSQL connection pool unavailable: {exc}") from exc

    def ping(self) -> bool:
        return self.pool.ping()

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description is None:
                    return []
                return cur.fetchall()

    def execute_transaction(self, statements: list[tuple[str, tuple[Any, ...]]]) -> None:
        """Execute a group atomically; either every statement commits or none does."""
        with self.pool.transaction() as conn:
            with conn.cursor() as cur:
                for query, params in statements:
                    cur.execute(query, params)

    def close(self) -> None:
        self.pool.close()

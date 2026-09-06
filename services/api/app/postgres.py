from __future__ import annotations

import os
from typing import Any


class PostgresStoreUnavailable(RuntimeError):
    """Raised when PostgreSQL persistence is requested but is not configured."""


class PostgresStore:
    """AETHON PostgreSQL adapter boundary.

    SQLite remains the default local backend. This adapter deliberately keeps the
    database dependency optional so AETHON can boot without PostgreSQL installed.
    """

    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.getenv("AETHON_DATABASE_URL")
        if not self.database_url:
            raise PostgresStoreUnavailable("AETHON_DATABASE_URL is not configured")
        if not self.database_url.startswith(("postgres://", "postgresql://")):
            raise PostgresStoreUnavailable("AETHON_DATABASE_URL must be a PostgreSQL URL")

    def ping(self) -> bool:
        try:
            import psycopg
        except ImportError as exc:
            raise PostgresStoreUnavailable("psycopg is not installed") from exc
        with psycopg.connect(self.database_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return cur.fetchone()[0] == 1

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        try:
            import psycopg
        except ImportError as exc:
            raise PostgresStoreUnavailable("psycopg is not installed") from exc
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                try:
                    return cur.fetchall()
                except psycopg.ProgrammingError:
                    return []

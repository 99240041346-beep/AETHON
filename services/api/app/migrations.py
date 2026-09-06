from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import psycopg


class MigrationError(RuntimeError):
    pass


class MigrationRunner:
    """Apply numbered SQL migrations exactly once using a PostgreSQL advisory lock."""

    def __init__(self, database_url: str, migrations_dir: str | Path | None = None):
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise MigrationError("Migration runner requires a PostgreSQL DATABASE URL")
        self.database_url = database_url
        self.migrations_dir = Path(migrations_dir or Path(__file__).resolve().parents[1] / "migrations")

    def migrations(self) -> list[Path]:
        files = sorted(self.migrations_dir.glob("[0-9][0-9][0-9]_*.sql"))
        if not files:
            raise MigrationError(f"No migrations found in {self.migrations_dir}")
        return files

    @staticmethod
    def _version(path: Path) -> str:
        return path.name.split("_", 1)[0]

    def ensure_tracking_table(self, conn: psycopg.Connection) -> None:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )"""
        )

    def applied(self, conn: psycopg.Connection) -> dict[str, tuple[str, str]]:
        rows = conn.execute("SELECT version, name, checksum FROM schema_migrations ORDER BY version").fetchall()
        return {row[0]: (row[1], row[2]) for row in rows}

    def plan(self, conn: psycopg.Connection) -> list[Path]:
        applied = self.applied(conn)
        pending: list[Path] = []
        for path in self.migrations():
            version = self._version(path)
            if version in applied:
                continue
            pending.append(path)
        return pending

    def migrate(self) -> list[str]:
        applied_versions: list[str] = []
        with psycopg.connect(self.database_url) as conn:
            # Serialize migration execution across API instances.
            conn.execute("SELECT pg_advisory_lock(hashtextextended('aethon:migrations', 0))")
            try:
                self.ensure_tracking_table(conn)
                applied = self.applied(conn)
                for path in self.migrations():
                    version = self._version(path)
                    sql = path.read_text(encoding="utf-8")
                    checksum = __import__("hashlib").sha256(sql.encode("utf-8")).hexdigest()
                    existing = applied.get(version)
                    if existing:
                        if existing[0] != path.name or existing[1] != checksum:
                            raise MigrationError(f"Migration {version} changed after it was applied")
                        continue
                    try:
                        conn.execute(sql)
                        conn.execute(
                            "INSERT INTO schema_migrations(version, name, checksum) VALUES (%s, %s, %s)",
                            (version, path.name, checksum),
                        )
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise MigrationError(f"Migration {path.name} failed") from None
                    applied_versions.append(version)
            finally:
                conn.execute("SELECT pg_advisory_unlock(hashtextextended('aethon:migrations', 0))")
        return applied_versions


def migrate_from_environment() -> list[str]:
    url = os.getenv("AETHON_DATABASE_URL")
    if not url:
        return []
    return MigrationRunner(url).migrate()

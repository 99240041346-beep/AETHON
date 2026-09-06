"""Compatibility export for PostgreSQL persistence."""
from app.postgres import PostgresStore, PostgresStoreUnavailable

__all__ = ["PostgresStore", "PostgresStoreUnavailable"]

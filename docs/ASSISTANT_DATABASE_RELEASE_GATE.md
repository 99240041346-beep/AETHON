# Assistant Database Release Gate

- Assistant sessions and messages are persisted with owner isolation.
- Language/locale metadata is stored with conversation messages.
- Device command state remains separate from conversation state.
- Migrations are additive, ordered, and deterministic.
- PostgreSQL is never silently replaced by SQLite when configured.
- Database tests and API tests are required before merge.

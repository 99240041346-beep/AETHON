# AETHON Assistant Runtime Database

Migration `006_assistant_runtime.sql` adds durable storage for the unified assistant experience.

## Tables

- `assistant_sessions`: owner/project-scoped conversation sessions.
- `assistant_messages`: ordered user/assistant/system/tool messages with language and intent metadata.
- `devices`: owner-bound device identity, platform, capabilities, and heartbeat state.
- `device_commands`: authenticated command lifecycle with capability, nonce, expiry, status, and verification.
- `tool_executions`: auditable tool execution outcomes and verification evidence.

## Security invariants

1. Every assistant runtime resource carries an `owner_id`.
2. Device commands use a unique nonce to support replay protection.
3. Commands have an explicit expiry timestamp.
4. Completion records whether execution was independently verified.
5. Database state never grants authorization; Safety Kernel and execution gates remain authoritative.
6. Capability data is descriptive and must not be interpreted as permission by the database layer.

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from aethon.postgres import PostgresStore


class CommandTransportError(ValueError):
    pass


@dataclass(frozen=True)
class PersistedCommand:
    command_id: str
    owner_id: str
    device_id: str
    capability: str
    arguments: dict[str, Any]
    nonce: str
    issued_at: float
    expires_at: float
    status: str


class AndroidCommandTransport:
    """PostgreSQL-backed command queue with atomic claim and result verification state."""

    MAX_TTL_SECONDS = 30

    def __init__(self, database_url: str | None = None):
        self.store = PostgresStore(database_url)

    @staticmethod
    def _ts(value: float) -> datetime:
        return datetime.fromtimestamp(value, tz=timezone.utc)

    def enqueue(self, *, owner_id: str, device_id: str, capability: str, arguments: dict[str, Any], nonce: str, approved: bool, ttl_seconds: float = 15) -> PersistedCommand:
        if not owner_id or not device_id or not capability or not nonce:
            raise CommandTransportError("owner, device, capability and nonce are required")
        if ttl_seconds <= 0 or ttl_seconds > self.MAX_TTL_SECONDS:
            raise CommandTransportError("invalid command TTL")
        command_id = str(uuid4())
        issued = time.time(); expires = issued + ttl_seconds
        try:
            self.store.execute(
                """INSERT INTO device_commands
                (command_id, owner_id, device_id, capability, arguments_json, nonce, status, verified, issued_at, expires_at)
                VALUES(%s,%s,%s,%s,%s::jsonb,%s,'ACCEPTED',FALSE,%s,%s)""",
                (command_id, owner_id, device_id, capability, json.dumps({**arguments, "_approved": approved}), nonce, self._ts(issued), self._ts(expires)),
            )
        except Exception as exc:
            raise CommandTransportError("command could not be persisted") from exc
        return PersistedCommand(command_id, owner_id, device_id, capability, arguments, nonce, issued, expires, "ACCEPTED")

    def claim_next(self, *, device_id: str, owner_id: str) -> PersistedCommand | None:
        """Atomically claim one unexpired command using row locking and SKIP LOCKED."""
        now = self._ts(time.time())
        rows = self.store.execute(
            """WITH next_command AS (
                   SELECT command_id FROM device_commands
                   WHERE device_id=%s AND owner_id=%s AND status='ACCEPTED' AND expires_at>%s
                   ORDER BY issued_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED
               )
               UPDATE device_commands AS dc SET claimed_at=NOW()
               FROM next_command WHERE dc.command_id=next_command.command_id
               RETURNING dc.command_id,dc.owner_id,dc.device_id,dc.capability,dc.arguments_json,dc.nonce,dc.issued_at,dc.expires_at,dc.status""",
            (device_id, owner_id, now),
        )
        if not rows:
            self.expire_pending(device_id=device_id, owner_id=owner_id); return None
        r = rows[0]; args = r[4] if isinstance(r[4], dict) else json.loads(r[4]); args.pop("_approved", None)
        return PersistedCommand(str(r[0]), r[1], r[2], r[3], args, r[5], r[6].timestamp(), r[7].timestamp(), r[8])

    def expire_pending(self, *, device_id: str, owner_id: str) -> int:
        rows = self.store.execute("""UPDATE device_commands SET status='EXPIRED' WHERE device_id=%s AND owner_id=%s AND status='ACCEPTED' AND expires_at<=NOW() RETURNING command_id""", (device_id, owner_id))
        return len(rows)

    def cancel(self, *, command_id: str, owner_id: str) -> bool:
        rows = self.store.execute("""UPDATE device_commands SET status='CANCELLED', completed_at=NOW(), error='cancelled by owner' WHERE command_id=%s AND owner_id=%s AND status='ACCEPTED' RETURNING command_id""", (command_id, owner_id))
        return bool(rows)

    def record_result(self, *, command_id: str, device_id: str, owner_id: str, success: bool, verified: bool, result: dict[str, Any] | None = None, verification: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:
        status = 'COMPLETED' if success and verified else 'REJECTED'
        rows = self.store.execute(
            """UPDATE device_commands SET status=%s, verified=%s, result_json=%s::jsonb, verification_json=%s::jsonb,
               error=%s, completed_at=NOW(), result_received_at=NOW()
               WHERE command_id=%s AND owner_id=%s AND device_id=%s AND status='ACCEPTED' AND expires_at>NOW()
               RETURNING command_id,status,verified,error""",
            (status, verified, json.dumps(result or {}), json.dumps(verification or {}), error, command_id, owner_id, device_id),
        )
        if not rows: raise CommandTransportError("command is missing, expired, cancelled, or already completed")
        r = rows[0]; return {"command_id": str(r[0]), "status": r[1], "verified": bool(r[2]), "error": r[3]}

    def get(self, *, command_id: str, owner_id: str) -> dict[str, Any] | None:
        rows = self.store.execute("""SELECT command_id,owner_id,device_id,capability,status,verified,error,issued_at,expires_at,claimed_at,completed_at,result_json,verification_json FROM device_commands WHERE command_id=%s AND owner_id=%s""", (command_id, owner_id))
        if not rows: return None
        r = rows[0]
        return {"command_id": str(r[0]), "owner_id": r[1], "device_id": r[2], "capability": r[3], "status": r[4], "verified": bool(r[5]), "error": r[6], "issued_at": r[7].isoformat(), "expires_at": r[8].isoformat(), "claimed_at": r[9].isoformat() if r[9] else None, "completed_at": r[10].isoformat() if r[10] else None, "result": r[11] if isinstance(r[11], dict) else (json.loads(r[11]) if r[11] else None), "verification": r[12] if isinstance(r[12], dict) else (json.loads(r[12]) if r[12] else None)}

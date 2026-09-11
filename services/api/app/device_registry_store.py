from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from aethon.postgres import PostgresStore


class DeviceRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredDevice:
    device_id: str
    owner_id: str
    platform: str
    capabilities: frozenset[str]
    token_hash: str
    last_seen: float
    registration_nonce: str


class DeviceRegistryStore:
    """PostgreSQL persistence boundary for device identity, capabilities and heartbeat state."""

    def __init__(self, database_url: str | None = None):
        self.store = PostgresStore(database_url)

    @staticmethod
    def _device(row: tuple[Any, ...]) -> StoredDevice:
        capabilities = row[3] if isinstance(row[3], list) else json.loads(row[3])
        return StoredDevice(str(row[0]), str(row[1]), str(row[2]), frozenset(capabilities), str(row[4]), row[5].timestamp(), str(row[6]))

    def create(self, *, device_id: str, owner_id: str, platform: str, capabilities: set[str], token_hash: str, registration_nonce: str) -> None:
        self.store.execute(
            """INSERT INTO device_registry
            (device_id, owner_id, platform, capabilities, token_hash, registration_nonce)
            VALUES(%s,%s,%s,%s::jsonb,%s,%s)""",
            (device_id, owner_id, platform, json.dumps(sorted(capabilities)), token_hash, registration_nonce),
        )

    def get(self, *, device_id: str) -> StoredDevice | None:
        rows = self.store.execute(
            "SELECT device_id,owner_id,platform,capabilities,token_hash,last_seen,registration_nonce FROM device_registry WHERE device_id=%s",
            (device_id,),
        )
        return self._device(rows[0]) if rows else None

    def heartbeat(self, *, device_id: str, owner_id: str) -> StoredDevice:
        rows = self.store.execute(
            """UPDATE device_registry SET last_seen=NOW(),updated_at=NOW()
               WHERE device_id=%s AND owner_id=%s
               RETURNING device_id,owner_id,platform,capabilities,token_hash,last_seen,registration_nonce""",
            (device_id, owner_id),
        )
        if not rows:
            raise DeviceRegistryError("device not found")
        return self._device(rows[0])

    def mark_replay_nonce(self, *, nonce: str, device_id: str, command_id: str) -> bool:
        rows = self.store.execute(
            """INSERT INTO device_replay_nonces(nonce,device_id,command_id)
               VALUES(%s,%s,%s) ON CONFLICT (nonce) DO NOTHING RETURNING nonce""",
            (nonce, device_id, command_id),
        )
        return bool(rows)

    def status(self, *, device_id: str, owner_id: str, heartbeat_ttl: float) -> dict[str, Any]:
        device = self.get(device_id=device_id)
        if not device or device.owner_id != owner_id:
            raise DeviceRegistryError("device not found")
        return {
            "device_id": device.device_id,
            "platform": device.platform,
            "capabilities": sorted(device.capabilities),
            "last_seen": device.last_seen,
            "online": time.time() - device.last_seen <= heartbeat_ttl,
        }

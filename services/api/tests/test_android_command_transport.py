from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aethon.android_command_transport import AndroidCommandTransport, CommandTransportError


class FakeStore:
    def __init__(self):
        self.rows = {}

    def execute(self, query, params=()):
        q = " ".join(query.split()).lower()
        if q.startswith("insert into device_commands"):
            command_id, owner, device, capability, args, nonce, status, verified, issued, expires = params
            if any(row["nonce"] == nonce for row in self.rows.values()):
                raise RuntimeError("duplicate nonce")
            self.rows[command_id] = {
                "owner": owner, "device": device, "capability": capability, "args": args,
                "nonce": nonce, "status": status, "verified": verified,
                "issued": issued, "expires": expires, "claimed": None, "completed": None,
                "error": None, "result": None, "verification": None,
            }
            return []
        if q.startswith("update device_commands set claimed_at"):
            device, owner, now = params
            candidates = [(k, v) for k, v in self.rows.items() if v["device"] == device and v["owner"] == owner and v["status"] == "ACCEPTED" and v["expires"] > now]
            if not candidates:
                return []
            command_id, row = sorted(candidates, key=lambda item: item[1]["issued"])[0]
            row["claimed"] = now
            return [(command_id, owner, device, row["capability"], row["args"], row["nonce"], row["issued"], row["expires"], row["status"])]
        if q.startswith("update device_commands set status='expired'"):
            device, owner = params
            now = datetime.now(timezone.utc)
            ids = []
            for command_id, row in self.rows.items():
                if row["device"] == device and row["owner"] == owner and row["status"] == "ACCEPTED" and row["expires"] <= now:
                    row["status"] = "EXPIRED"; ids.append((command_id,))
            return ids
        if q.startswith("update device_commands set status='cancelled'"):
            command_id, owner = params
            row = self.rows.get(command_id)
            if row and row["owner"] == owner and row["status"] == "ACCEPTED":
                row["status"] = "CANCELLED"; return [(command_id,)]
            return []
        if q.startswith("update device_commands set status=%s"):
            status, verified, result, verification, error, command_id, owner, device = params
            row = self.rows.get(command_id)
            if not row or row["owner"] != owner or row["device"] != device or row["status"] != "ACCEPTED" or row["expires"] <= datetime.now(timezone.utc):
                return []
            row.update(status=status, verified=verified, result=result, verification=verification, error=error)
            return [(command_id, status, verified, error)]
        if q.startswith("select command_id,owner_id,device_id,capability,status"):
            command_id, owner = params
            row = self.rows.get(command_id)
            if not row or row["owner"] != owner: return []
            return [(command_id, owner, row["device"], row["capability"], row["status"], row["verified"], row["error"], row["issued"], row["expires"], row["claimed"], row["completed"], row["result"], row["verification"])]
        raise AssertionError(q)


def transport():
    t = AndroidCommandTransport.__new__(AndroidCommandTransport)
    t.store = FakeStore()
    return t


def test_enqueue_claim_and_verified_completion():
    t = transport()
    command = t.enqueue(owner_id="owner-a", device_id="phone-1", capability="OPEN_APP", arguments={"package": "com.google.android.youtube"}, nonce="nonce-12345678", approved=True)
    claimed = t.claim_next(device_id="phone-1", owner_id="owner-a")
    assert claimed and claimed.command_id == command.command_id
    result = t.record_result(command_id=command.command_id, device_id="phone-1", owner_id="owner-a", success=True, verified=True, verification={"package_visible": True})
    assert result["status"] == "COMPLETED" and result["verified"] is True


def test_replay_nonce_is_rejected_by_persistence_boundary():
    t = transport()
    t.enqueue(owner_id="owner-a", device_id="phone-1", capability="OPEN_APP", arguments={}, nonce="nonce-12345678", approved=True)
    with pytest.raises(CommandTransportError):
        t.enqueue(owner_id="owner-a", device_id="phone-1", capability="OPEN_APP", arguments={}, nonce="nonce-12345678", approved=True)


def test_wrong_owner_cannot_read_or_cancel():
    t = transport()
    command = t.enqueue(owner_id="owner-a", device_id="phone-1", capability="OPEN_APP", arguments={}, nonce="nonce-12345678", approved=True)
    assert t.get(command_id=command.command_id, owner_id="owner-b") is None
    assert t.cancel(command_id=command.command_id, owner_id="owner-b") is False

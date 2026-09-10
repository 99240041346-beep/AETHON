from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Any
from uuid import uuid4


class AndroidCapability(str, Enum):
    OPEN_APP = "OPEN_APP"


class CommandStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class AndroidCommand:
    command_id: str
    owner_id: str
    device_id: str
    capability: AndroidCapability
    arguments: dict[str, Any]
    nonce: str
    expires_at: float


@dataclass(frozen=True)
class CommandReceipt:
    command_id: str
    status: CommandStatus
    capability: AndroidCapability
    verified: bool = False


class AndroidCommandBridge:
    """Bounded command contract; validates commands but never executes Android APIs."""

    MAX_TTL_SECONDS = 30.0

    def __init__(self) -> None:
        self._used_nonces: set[str] = set()

    def issue_open_app(
        self,
        *,
        owner_id: str,
        device_id: str,
        package_name: str,
        ttl_seconds: float = 15.0,
    ) -> AndroidCommand:
        if not owner_id or not device_id:
            raise ValueError("owner and device are required")
        if not package_name or len(package_name) > 200:
            raise ValueError("invalid Android package name")
        if ttl_seconds <= 0 or ttl_seconds > self.MAX_TTL_SECONDS:
            raise ValueError("invalid command TTL")
        return AndroidCommand(
            command_id=str(uuid4()),
            owner_id=owner_id,
            device_id=device_id,
            capability=AndroidCapability.OPEN_APP,
            arguments={"package_name": package_name},
            nonce=str(uuid4()),
            expires_at=monotonic() + ttl_seconds,
        )

    def accept(self, command: AndroidCommand, *, owner_id: str, device_id: str) -> CommandReceipt:
        if command.owner_id != owner_id or command.device_id != device_id:
            return CommandReceipt(command.command_id, CommandStatus.REJECTED, command.capability)
        if monotonic() >= command.expires_at:
            return CommandReceipt(command.command_id, CommandStatus.REJECTED, command.capability)
        if command.nonce in self._used_nonces:
            return CommandReceipt(command.command_id, CommandStatus.REJECTED, command.capability)
        self._used_nonces.add(command.nonce)
        return CommandReceipt(command.command_id, CommandStatus.ACCEPTED, command.capability)

    def complete(self, receipt: CommandReceipt, *, verified: bool) -> CommandReceipt:
        if receipt.status is not CommandStatus.ACCEPTED:
            return receipt
        if not verified:
            return CommandReceipt(receipt.command_id, CommandStatus.REJECTED, receipt.capability, False)
        return CommandReceipt(receipt.command_id, CommandStatus.COMPLETED, receipt.capability, True)

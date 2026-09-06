from __future__ import annotations

# Compatibility export for the canonical aethon package namespace.
from app.distributed_persistence import DistributedTaskPersistence, RecoveryCandidate

__all__ = ["DistributedTaskPersistence", "RecoveryCandidate"]

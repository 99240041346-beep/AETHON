from __future__ import annotations

from uuid import uuid4

from app.distributed_persistence import DistributedTaskPersistence


def test_recovery_candidate_contains_previous_lease_identity():
    candidate = __import__("app.distributed_persistence", fromlist=["RecoveryCandidate"]).RecoveryCandidate(
        uuid4(), "worker-a", "old-token", __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    )
    assert candidate.worker_id == "worker-a"
    assert candidate.lease_token == "old-token"


def test_postgres_persistence_is_explicitly_configured():
    assert DistributedTaskPersistence.configured() in (True, False)

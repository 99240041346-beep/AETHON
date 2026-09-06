from __future__ import annotations

import os
import threading
from uuid import uuid4

import pytest

from aethon.distributed_persistence import DistributedTaskPersistence
from aethon.postgres_task_store import PostgreSQLTaskStore
from aethon.schemas import TaskStatus


pytestmark = pytest.mark.integration


def database_url() -> str:
    value = os.getenv("AETHON_DATABASE_URL", "")
    if not value.startswith(("postgres://", "postgresql://")):
        pytest.skip("AETHON_DATABASE_URL is not configured for PostgreSQL integration tests")
    return value


def test_two_workers_competing_for_same_task_only_one_claims():
    url = database_url()
    persistence = DistributedTaskPersistence(url)
    store = PostgreSQLTaskStore(url)
    task_id = uuid4()
    store.postgres.execute(
        "INSERT INTO tasks(task_id,goal,owner_id,priority,status) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(task_id) DO NOTHING",
        (str(task_id), "distributed claim test", "integration-test", 5, TaskStatus.QUEUED.value),
    )
    store.postgres.execute("DELETE FROM worker_leases WHERE task_id=%s", (str(task_id),))

    barrier = threading.Barrier(2)
    results: list[str | None] = [None, None]

    def claim(index: int, worker: str) -> None:
        barrier.wait()
        results[index] = persistence.acquire_lease(task_id, worker, 30)

    threads = [
        threading.Thread(target=claim, args=(0, "worker-a")),
        threading.Thread(target=claim, args=(1, "worker-b")),
    ]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=10)

    winners = [token for token in results if token is not None]
    assert len(winners) == 1
    rows = persistence.store.execute("SELECT worker_id,lease_token FROM worker_leases WHERE task_id=%s", (str(task_id),))
    assert len(rows) == 1
    assert rows[0][1] == winners[0]

    persistence.release_lease(task_id, rows[0][0], rows[0][1])
    store.postgres.execute("DELETE FROM tasks WHERE task_id=%s", (str(task_id),))


def test_expired_lease_can_be_reclaimed_by_another_worker():
    url = database_url()
    persistence = DistributedTaskPersistence(url)
    store = PostgreSQLTaskStore(url)
    task_id = uuid4()
    store.postgres.execute(
        "INSERT INTO tasks(task_id,goal,owner_id,priority,status) VALUES(%s,%s,%s,%s,%s)",
        (str(task_id), "lease expiry test", "integration-test", 5, TaskStatus.QUEUED.value),
    )
    store.postgres.execute("""INSERT INTO worker_leases(task_id,worker_id,lease_token,expires_at)
        VALUES(%s,'dead-worker','dead-token',NOW()-INTERVAL '1 second')""", (str(task_id),))

    token = persistence.acquire_lease(task_id, "recovery-worker", 30)
    assert token
    rows = persistence.store.execute("SELECT worker_id,lease_token,expires_at > NOW() FROM worker_leases WHERE task_id=%s", (str(task_id),))
    assert rows[0][0] == "recovery-worker"
    assert rows[0][1] == token
    assert rows[0][2] is True

    persistence.release_lease(task_id, "recovery-worker", token)
    store.postgres.execute("DELETE FROM tasks WHERE task_id=%s", (str(task_id),))

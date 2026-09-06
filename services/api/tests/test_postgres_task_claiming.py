import os
import threading
from uuid import uuid4

import pytest

from aethon.distributed_persistence import DistributedTaskPersistence


pytestmark = pytest.mark.integration


def _db_url():
    return os.getenv("AETHON_DATABASE_URL")


def _seed_task(persistence, priority=5):
    task_id = uuid4()
    persistence.store.execute(
        """INSERT INTO tasks(task_id,goal,project_id,owner_id,priority,status,result_json,error)
           VALUES(%s,%s,%s,%s,%s,'QUEUED',NULL,NULL)""",
        (str(task_id), "atomic claim test", None, "integration", priority),
    )
    return task_id


def test_competing_workers_claim_each_task_once():
    if not _db_url():
        pytest.skip("AETHON_DATABASE_URL is not configured")
    persistence = DistributedTaskPersistence(_db_url())
    persistence.ensure_schema()
    task_ids = [_seed_task(persistence, priority=i) for i in range(5)]
    barrier = threading.Barrier(10)
    results = []
    lock = threading.Lock()

    def worker(index):
        local = DistributedTaskPersistence(_db_url())
        barrier.wait()
        claimed = local.claim_next_task(f"claim-worker-{index}", lease_seconds=30)
        with lock:
            results.append(claimed)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    claimed = [item for item in results if item is not None]
    assert len(claimed) == 5
    assert len({item.task_id for item in claimed}) == 5
    assert {item.task_id for item in claimed} == set(task_ids)


def test_claim_prefers_priority_then_fifo():
    if not _db_url():
        pytest.skip("AETHON_DATABASE_URL is not configured")
    persistence = DistributedTaskPersistence(_db_url())
    persistence.ensure_schema()
    low = _seed_task(persistence, priority=1)
    _seed_task(persistence, priority=5)
    claimed = persistence.claim_next_task("priority-worker", lease_seconds=30)
    assert claimed is not None
    assert claimed.task_id == low

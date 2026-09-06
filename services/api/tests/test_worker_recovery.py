from aethon.worker_lease import WorkerLeaseStore
from aethon.worker_recovery import WorkerRecoveryCoordinator


def test_recovery_reclaims_expired_work(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    leases.acquire("task-old", "dead-worker", ttl_seconds=0.01)
    import time
    time.sleep(0.03)
    submitted = []
    tasks = ["task-old", "task-new"]

    coordinator = WorkerRecoveryCoordinator(
        leases,
        list_recoverable=lambda: tasks,
        task_id=lambda task: task,
        submit=lambda task: submitted.append(task),
    )
    result = coordinator.recover_once()

    assert result.expired_leases == 1
    assert result.recovered_tasks == 2
    assert submitted == tasks


def test_recovery_skips_currently_leased_work(tmp_path):
    leases = WorkerLeaseStore(str(tmp_path / "leases.db"))
    leases.acquire("task-live", "worker-a", ttl_seconds=1)
    submitted = []

    coordinator = WorkerRecoveryCoordinator(
        leases,
        list_recoverable=lambda: ["task-live"],
        task_id=lambda task: task,
        submit=lambda task: submitted.append(task),
    )
    result = coordinator.recover_once()

    assert result.recovered_tasks == 0
    assert result.skipped_tasks == 1
    assert submitted == []

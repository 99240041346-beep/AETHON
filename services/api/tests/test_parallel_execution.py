from threading import Lock
from time import sleep

from aethon.parallel_execution import ParallelTaskExecutor
from aethon.task_graph import TaskGraphPlanner


def test_independent_tasks_run_in_parallel_and_dependents_wait():
    graph = TaskGraphPlanner().build(
        ["A", "B", "C"],
        {"C": ["A", "B"]},
    )
    active = 0
    peak = 0
    lock = Lock()

    def handler(node):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        sleep(0.03)
        with lock:
            active -= 1
        return node.goal

    report = ParallelTaskExecutor(max_workers=2).execute(
        graph,
        handler,
        safety_check=lambda node: True,
        verifier=lambda node, value: value == node.goal,
    )

    assert peak == 2
    assert [result.status for result in report.results] == ["SUCCEEDED"] * 3
    assert [result.task_id for result in report.results] == ["task-1", "task-2", "task-3"]


def test_safety_gate_rejects_without_execution():
    graph = TaskGraphPlanner().build(["safe", "blocked"])
    executed = []

    report = ParallelTaskExecutor().execute(
        graph,
        lambda node: executed.append(node.goal) or node.goal,
        safety_check=lambda node: node.goal == "safe",
        verifier=lambda node, value: True,
    )

    assert executed == ["safe"]
    assert [result.status for result in report.results] == ["SUCCEEDED", "REJECTED"]


def test_verification_failure_is_retried_and_then_fails():
    graph = TaskGraphPlanner().build(["check"])
    attempts = 0

    def handler(node):
        nonlocal attempts
        attempts += 1
        return attempts

    report = ParallelTaskExecutor(max_retries=2).execute(
        graph,
        handler,
        safety_check=lambda node: True,
        verifier=lambda node, value: False,
    )

    assert attempts == 3
    assert report.results[0].status == "FAILED"
    assert report.results[0].attempts == 3


def test_failed_dependency_blocks_dependents_but_unrelated_task_runs():
    graph = TaskGraphPlanner().build(
        ["fail", "dependent", "independent"],
        {"dependent": ["fail"]},
    )

    report = ParallelTaskExecutor().execute(
        graph,
        lambda node: (_ for _ in ()).throw(RuntimeError("boom"))
        if node.goal == "fail"
        else node.goal,
        safety_check=lambda node: True,
        verifier=lambda node, value: True,
    )

    statuses = {result.task_id: result.status for result in report.results}
    assert statuses["task-1"] == "FAILED"
    assert statuses["task-2"] == "BLOCKED"
    assert statuses["task-3"] == "SUCCEEDED"


def test_cancellation_is_bounded():
    graph = TaskGraphPlanner().build(["one", "two"])
    cancelled = False

    def cancel_check():
        return cancelled

    def handler(node):
        sleep(0.01)
        return node.goal

    cancelled = True
    report = ParallelTaskExecutor().execute(
        graph,
        handler,
        safety_check=lambda node: True,
        verifier=lambda node, value: True,
        cancel_check=cancel_check,
    )

    assert report.cancelled is True
    assert all(result.status == "CANCELLED" for result in report.results)

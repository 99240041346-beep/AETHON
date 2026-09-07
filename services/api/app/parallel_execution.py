from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from time import monotonic
from typing import Callable, TypeVar

from .task_graph import TaskGraph, TaskNode

T = TypeVar("T")


@dataclass(frozen=True)
class TaskExecutionResult:
    task_id: str
    status: str
    attempts: int
    result: object | None = None
    error: str | None = None


@dataclass(frozen=True)
class ParallelExecutionReport:
    results: tuple[TaskExecutionResult, ...]
    cancelled: bool


class ParallelTaskExecutor:
    """Execute a TaskGraph in bounded dependency-aware waves.

    This is an execution primitive, not an authority system. Every task must
    pass the supplied safety gate immediately before execution and every
    successful execution must pass the supplied verifier.
    """

    def __init__(
        self,
        *,
        max_workers: int = 4,
        max_retries: int = 0,
        max_tasks: int = 100,
        max_execution_seconds: float = 300.0,
    ) -> None:
        if not 1 <= max_workers <= 32:
            raise ValueError("max_workers must be between 1 and 32")
        if not 0 <= max_retries <= 10:
            raise ValueError("max_retries must be between 0 and 10")
        if not 1 <= max_tasks <= 1000:
            raise ValueError("max_tasks must be between 1 and 1000")
        if max_execution_seconds <= 0:
            raise ValueError("max_execution_seconds must be > 0")
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.max_tasks = max_tasks
        self.max_execution_seconds = max_execution_seconds

    def execute(
        self,
        graph: TaskGraph,
        handler: Callable[[TaskNode], T],
        *,
        safety_check: Callable[[TaskNode], bool],
        verifier: Callable[[TaskNode, T], bool],
        cancel_check: Callable[[], bool] | None = None,
    ) -> ParallelExecutionReport:
        """Run the graph until completion, cancellation, or a bounded deadline."""
        if len(graph.nodes) > self.max_tasks:
            raise ValueError("task graph exceeds max_tasks")

        started = monotonic()
        cancel_check = cancel_check or (lambda: False)
        pending = {node.id: node for node in graph.nodes}
        completed: set[str] = set()
        failed: set[str] = set()
        results: dict[str, TaskExecutionResult] = {}
        cancelled = False

        executor = ThreadPoolExecutor(max_workers=self.max_workers)
        try:
            while pending:
                if cancel_check() or monotonic() - started >= self.max_execution_seconds:
                    cancelled = True
                    for node in pending.values():
                        results[node.id] = TaskExecutionResult(node.id, "CANCELLED", 0)
                    break

                ready = tuple(
                    node
                    for node in graph.nodes
                    if node.id in pending
                    and all(dependency in completed for dependency in node.depends_on)
                )

                blocked = tuple(
                    node
                    for node in graph.nodes
                    if node.id in pending
                    and any(dependency in failed for dependency in node.depends_on)
                )
                for node in blocked:
                    pending.pop(node.id, None)
                    results[node.id] = TaskExecutionResult(
                        node.id, "BLOCKED", 0, error="dependency failed"
                    )

                if not ready:
                    if pending:
                        for node in tuple(pending.values()):
                            results[node.id] = TaskExecutionResult(
                                node.id, "BLOCKED", 0, error="unresolvable dependency graph"
                            )
                            pending.pop(node.id, None)
                    continue

                futures: dict[str, Future[tuple[str, int, object | None, str | None]]] = {}
                for node in ready:
                    if cancel_check() or monotonic() - started >= self.max_execution_seconds:
                        cancelled = True
                        break
                    try:
                        allowed = safety_check(node)
                    except BaseException as exc:
                        allowed = False
                        results[node.id] = TaskExecutionResult(
                            node.id, "REJECTED", 0, error=str(exc)
                        )
                    if not allowed:
                        pending.pop(node.id, None)
                        failed.add(node.id)
                        results.setdefault(
                            node.id,
                            TaskExecutionResult(node.id, "REJECTED", 0, error="safety check rejected task"),
                        )
                        continue
                    futures[node.id] = executor.submit(
                        self._run_with_retries, node, handler, verifier, cancel_check
                    )

                for node in ready:
                    future = futures.get(node.id)
                    if future is None:
                        continue
                    try:
                        status, attempts, value, error = future.result(
                            timeout=max(0.0, self.max_execution_seconds - (monotonic() - started))
                        )
                    except BaseException as exc:
                        status, attempts, value, error = "FAILED", 1, None, str(exc)
                    pending.pop(node.id, None)
                    results[node.id] = TaskExecutionResult(node.id, status, attempts, value, error)
                    if status == "SUCCEEDED":
                        completed.add(node.id)
                    else:
                        failed.add(node.id)

                if cancelled:
                    for node in pending.values():
                        results[node.id] = TaskExecutionResult(node.id, "CANCELLED", 0)
                    break
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        ordered = tuple(results[node.id] for node in graph.nodes if node.id in results)
        return ParallelExecutionReport(ordered, cancelled)

    def _run_with_retries(
        self,
        node: TaskNode,
        handler: Callable[[TaskNode], T],
        verifier: Callable[[TaskNode, T], bool],
        cancel_check: Callable[[], bool],
    ) -> tuple[str, int, object | None, str | None]:
        last_error: str | None = None
        for attempt in range(1, self.max_retries + 2):
            if cancel_check():
                return "CANCELLED", attempt - 1, None, None
            try:
                value = handler(node)
                if not verifier(node, value):
                    last_error = "verification failed"
                    continue
                return "SUCCEEDED", attempt, value, None
            except BaseException as exc:
                last_error = str(exc)
        return "FAILED", self.max_retries + 1, None, last_error

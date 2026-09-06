from __future__ import annotations

import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Generic, Iterable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class _Queued(Generic[T]):
    priority: int
    sequence: int
    item: T
    future: Future
    dependencies: tuple[Future, ...] = field(default_factory=tuple)
    resources: dict[str, int] = field(default_factory=dict)


class TaskScheduler(Generic[T, R]):
    """Bounded priority scheduler with dependency-aware admission and resource quotas."""

    def __init__(
        self,
        worker: Callable[[T], R],
        max_workers: int | None = None,
        resource_limits: dict[str, int] | None = None,
    ):
        configured = max_workers or int(os.getenv("AETHON_MAX_CONCURRENT_TASKS", "4"))
        if configured < 1:
            raise ValueError("max_workers must be >= 1")
        limits = dict(resource_limits or {})
        if any(not name or amount < 1 for name, amount in limits.items()):
            raise ValueError("resource limits must be positive")
        self.max_workers = configured
        self.resource_limits = limits
        self._worker = worker
        self._executor = ThreadPoolExecutor(max_workers=configured, thread_name_prefix="aethon-agent")
        self._condition = threading.Condition()
        self._queue: list[_Queued[T]] = []
        self._sequence = 0
        self._active = 0
        self._resources_in_use: dict[str, int] = {name: 0 for name in limits}
        self._closed = False
        self._dispatcher = threading.Thread(target=self._dispatch, name="aethon-scheduler", daemon=True)
        self._dispatcher.start()

    def submit(
        self,
        item: T,
        priority: int = 5,
        dependencies: Iterable[Future] | None = None,
        resources: dict[str, int] | None = None,
    ) -> Future:
        if not 1 <= priority <= 10:
            raise ValueError("priority must be between 1 and 10")
        requested = dict(resources or {})
        if any(not name or amount < 1 for name, amount in requested.items()):
            raise ValueError("resource requests must be positive")
        for name, amount in requested.items():
            limit = self.resource_limits.get(name)
            if limit is None:
                raise ValueError(f"unknown resource: {name}")
            if amount > limit:
                raise ValueError(f"resource request exceeds limit: {name}")
        future: Future = Future()
        with self._condition:
            if self._closed:
                raise RuntimeError("scheduler is closed")
            self._sequence += 1
            self._queue.append(_Queued(priority, self._sequence, item, future, tuple(dependencies or ()), requested))
            self._condition.notify_all()
        return future

    def submit_and_wait(
        self,
        item: T,
        priority: int = 5,
        timeout: float | None = None,
        dependencies: Iterable[Future] | None = None,
        resources: dict[str, int] | None = None,
    ) -> R:
        return self.submit(item, priority, dependencies=dependencies, resources=resources).result(timeout=timeout)

    def snapshot(self) -> dict[str, object]:
        with self._condition:
            return {
                "queued": len(self._queue),
                "active": self._active,
                "max_workers": self.max_workers,
                "resource_limits": dict(self.resource_limits),
                "resources_in_use": dict(self._resources_in_use),
            }

    def shutdown(self, wait: bool = True) -> None:
        with self._condition:
            self._closed = True
            for queued in self._queue:
                queued.future.set_exception(RuntimeError("scheduler shut down before task execution"))
            self._queue.clear()
            self._condition.notify_all()
        self._executor.shutdown(wait=wait)

    def _dispatch(self) -> None:
        while True:
            with self._condition:
                while not self._closed and (not self._queue or self._active >= self.max_workers):
                    self._condition.wait()
                if self._closed and self._active == 0:
                    return
                candidate_index = self._select_candidate()
                if candidate_index is None:
                    if self._dependencies_failed():
                        continue
                    self._condition.wait(timeout=0.05)
                    continue
                queued = self._queue.pop(candidate_index)
                self._active += 1
                for name, amount in queued.resources.items():
                    self._resources_in_use[name] += amount
            submitted = self._executor.submit(self._run, queued)
            submitted.add_done_callback(lambda _: self._notify_capacity(queued.resources))

    def _select_candidate(self) -> int | None:
        eligible: list[tuple[int, int, int]] = []
        for index, queued in enumerate(self._queue):
            if any(not dependency.done() for dependency in queued.dependencies):
                continue
            if any(dependency.cancelled() or dependency.exception() is not None for dependency in queued.dependencies):
                continue
            if not self._resources_available(queued.resources):
                continue
            eligible.append((queued.priority, queued.sequence, index))
        if not eligible:
            return None
        return min(eligible)[2]

    def _resources_available(self, requested: dict[str, int]) -> bool:
        return all(self._resources_in_use[name] + amount <= self.resource_limits[name] for name, amount in requested.items())

    def _dependencies_failed(self) -> bool:
        for queued in self._queue:
            failed = next((dependency for dependency in queued.dependencies if dependency.done() and (dependency.cancelled() or dependency.exception() is not None)), None)
            if failed is not None:
                queued.future.set_exception(RuntimeError("scheduler dependency failed"))
                self._queue.remove(queued)
                return True
        return False

    def _notify_capacity(self, resources: dict[str, int]) -> None:
        with self._condition:
            self._active -= 1
            for name, amount in resources.items():
                self._resources_in_use[name] -= amount
            self._condition.notify_all()

    def _run(self, queued: _Queued[T]) -> None:
        if queued.future.cancelled():
            return
        try:
            queued.future.set_result(self._worker(queued.item))
        except BaseException as exc:
            queued.future.set_exception(exc)

from __future__ import annotations

import heapq
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass(order=True)
class _Queued(Generic[T]):
    priority: int
    sequence: int
    item: T = field(compare=False)
    future: Future = field(compare=False)


class TaskScheduler(Generic[T, R]):
    """Bounded priority scheduler for concurrent agent tasks."""

    def __init__(self, worker: Callable[[T], R], max_workers: int | None = None):
        configured = max_workers or int(os.getenv("AETHON_MAX_CONCURRENT_TASKS", "4"))
        if configured < 1:
            raise ValueError("max_workers must be >= 1")
        self.max_workers = configured
        self._worker = worker
        self._executor = ThreadPoolExecutor(max_workers=configured, thread_name_prefix="aethon-agent")
        self._condition = threading.Condition()
        self._queue: list[_Queued[T]] = []
        self._sequence = 0
        self._active = 0
        self._closed = False
        self._dispatcher = threading.Thread(target=self._dispatch, name="aethon-scheduler", daemon=True)
        self._dispatcher.start()

    def submit(self, item: T, priority: int = 5) -> Future:
        if not 1 <= priority <= 10:
            raise ValueError("priority must be between 1 and 10")
        future: Future = Future()
        with self._condition:
            if self._closed:
                raise RuntimeError("scheduler is closed")
            self._sequence += 1
            heapq.heappush(self._queue, _Queued(priority, self._sequence, item, future))
            self._condition.notify()
        return future

    def submit_and_wait(self, item: T, priority: int = 5, timeout: float | None = None) -> R:
        return self.submit(item, priority).result(timeout=timeout)

    def snapshot(self) -> dict[str, int]:
        with self._condition:
            return {"queued": len(self._queue), "active": self._active, "max_workers": self.max_workers}

    def shutdown(self, wait: bool = True) -> None:
        with self._condition:
            self._closed = True
            while self._queue:
                queued = heapq.heappop(self._queue)
                queued.future.set_exception(RuntimeError("scheduler shut down before task execution"))
            self._condition.notify_all()
        self._executor.shutdown(wait=wait)

    def _dispatch(self) -> None:
        while True:
            with self._condition:
                while not self._closed and (not self._queue or self._active >= self.max_workers):
                    self._condition.wait()
                if self._closed and not self._queue and self._active == 0:
                    return
                queued = heapq.heappop(self._queue)
                self._active += 1
            submitted = self._executor.submit(self._run, queued)
            submitted.add_done_callback(lambda _: self._notify_capacity())

    def _notify_capacity(self) -> None:
        with self._condition:
            self._active -= 1
            self._condition.notify_all()

    def _run(self, queued: _Queued[T]) -> None:
        if queued.future.cancelled():
            return
        try:
            queued.future.set_result(self._worker(queued.item))
        except BaseException as exc:
            queued.future.set_exception(exc)

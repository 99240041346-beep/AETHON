from uuid import uuid4

from aethon.execution_guard import ExecutionGuard


class Store:
    def __init__(self, update_rows=None, state='QUEUED'):
        self.update_rows = update_rows or []
        self.state = state
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((query, params))
        if query.startswith('UPDATE tasks'):
            return self.update_rows
        if query.startswith('SELECT status'):
            return [(self.state,)]
        return []


class Persistence:
    def __init__(self, store):
        self.store = store
        self.released = []

    def release_lease(self, task_id, worker_id, token):
        self.released.append((task_id, worker_id, token))
        return True


def test_completion_is_fenced_and_releases_lease():
    task_id = uuid4()
    p = Persistence(Store(update_rows=[(str(task_id),)]))
    result = ExecutionGuard(p).complete(task_id, 'w1', 't1', '{"ok":true}')
    assert result.applied is True
    assert p.released == [(task_id, 'w1', 't1')]


def test_duplicate_completion_is_idempotent():
    task_id = uuid4()
    p = Persistence(Store(state='SUCCEEDED'))
    result = ExecutionGuard(p).complete(task_id, 'stale-worker', 'old-token', '{"ok":true}')
    assert result.applied is False
    assert result.already_completed is True


def test_stale_worker_cannot_mark_failure():
    task_id = uuid4()
    p = Persistence(Store())
    assert ExecutionGuard(p).fail(task_id, 'stale-worker', 'old-token', 'boom') is False

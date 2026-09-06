from __future__ import annotations

import json
import os
import socket
import threading
from concurrent.futures import Future
from datetime import datetime, timezone
from uuid import UUID

from aethon.agent import AgentRuntime
from aethon.agent_state import AgentStateStore
from aethon.distributed_persistence import DistributedTaskPersistence
from aethon.postgres import PostgresStore
from aethon.scheduler import TaskScheduler
from aethon.schemas import Event, Task, TaskCreate, TaskStatus
from aethon.worker_pool import LeasedWorkerPool


class PostgreSQLTaskStore:
    """Shared PostgreSQL task store used when AETHON_DATABASE_URL is configured."""

    def __init__(self, database_url: str | None = None):
        self.postgres = PostgresStore(database_url)
        self.database_url = self.postgres.database_url
        self.worker_id = os.getenv("AETHON_WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"
        self.state_store = AgentStateStore(os.getenv("AETHON_AGENT_STATE_PATH", ".aethon/agent_state.db"))
        self.runtime = AgentRuntime(state_store=self.state_store)
        self.distributed = DistributedTaskPersistence(self.database_url)
        self._init_db()
        self.distributed.ensure_schema()
        lease_adapter = _PostgresLeaseAdapter(self.distributed)
        self.lease_store = lease_adapter
        self.worker_pool = LeasedWorkerPool(self.runtime.run, lease_adapter, self.worker_id,
            lease_seconds=float(os.getenv("AETHON_WORKER_LEASE_SECONDS", "30")),
            heartbeat_seconds=float(os.getenv("AETHON_WORKER_HEARTBEAT_SECONDS", "5")))
        self.scheduler = TaskScheduler(self.runtime.run, worker_pool=self.worker_pool, lease_key=lambda task: str(task.task_id))
        self._futures: dict[UUID, Future] = {}
        self._future_lock = threading.Lock()

    def _init_db(self) -> None:
        self.postgres.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id UUID PRIMARY KEY, goal TEXT NOT NULL, project_id TEXT,
            owner_id TEXT NOT NULL DEFAULT 'local-dev', priority INTEGER NOT NULL DEFAULT 5,
            status TEXT NOT NULL, result_json JSONB, error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id UUID PRIMARY KEY, task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            type TEXT NOT NULL, data_json JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            audit_id UUID PRIMARY KEY, task_id UUID REFERENCES tasks(task_id) ON DELETE CASCADE,
            action TEXT NOT NULL, data_json JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_events_task ON events(task_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_tasks_recovery ON tasks(status, priority, created_at);
        """)

    def _persist_task(self, task: Task) -> None:
        self.postgres.execute("""INSERT INTO tasks(task_id,goal,project_id,owner_id,priority,status,result_json,error,created_at,updated_at)
        VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb,%s,NOW(),NOW())
        ON CONFLICT(task_id) DO UPDATE SET goal=EXCLUDED.goal,project_id=EXCLUDED.project_id,
        owner_id=EXCLUDED.owner_id,priority=EXCLUDED.priority,status=EXCLUDED.status,
        result_json=EXCLUDED.result_json,error=EXCLUDED.error,updated_at=NOW()""",
        (str(task.task_id),task.goal,task.project_id,task.owner_id,task.priority,task.status.value,json.dumps(task.result),task.error))

    def _persist_events(self, task_id: UUID) -> None:
        for event in self.runtime.events.get(task_id, []):
            self.postgres.execute("INSERT INTO events(event_id,task_id,type,data_json,created_at) VALUES(%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(event_id) DO NOTHING",
                (str(event.event_id),str(event.task_id),event.type,json.dumps(event.data)))
            if event.type.startswith("audit."):
                self.postgres.execute("INSERT INTO audit_log(audit_id,task_id,action,data_json,created_at) VALUES(%s,%s,%s,%s::jsonb,NOW()) ON CONFLICT(audit_id) DO NOTHING",
                    (str(event.event_id),str(event.task_id),event.type[6:],json.dumps(event.data)))

    def _submit(self, task: Task) -> Future:
        future = self.scheduler.submit(task, priority=task.priority)
        with self._future_lock: self._futures[task.task_id] = future
        return future

    def _forget_future(self, task_id: UUID) -> None:
        with self._future_lock: self._futures.pop(task_id, None)

    def create(self, request: TaskCreate) -> Task:
        task = Task(goal=request.goal,project_id=request.project_id,priority=request.priority,owner_id=request.owner_id)
        self._persist_task(task); self.runtime._event(task,"task.queued",{"priority":task.priority,"scheduler":"bounded-thread-pool","worker_id":self.worker_id}); self._persist_events(task.task_id)
        future=self._submit(task)
        try: result=future.result()
        finally: self._forget_future(task.task_id)
        self._persist_task(result); self._persist_events(result.task_id); return result

    def get(self, task_id: UUID) -> Task | None:
        rows=self.postgres.execute("SELECT task_id,goal,project_id,priority,owner_id,status,result_json,error FROM tasks WHERE task_id=%s",(str(task_id),))
        if not rows:return None
        r=rows[0]; result=r[6] if not isinstance(r[6],str) else json.loads(r[6])
        return Task(task_id=UUID(str(r[0])),goal=r[1],project_id=r[2],priority=r[3],owner_id=r[4],status=r[5],result=result,error=r[7])

    def events(self, task_id: UUID) -> list[Event]:
        rows=self.postgres.execute("SELECT event_id,task_id,type,data_json FROM events WHERE task_id=%s ORDER BY created_at",(str(task_id),))
        return [Event(event_id=UUID(str(r[0])),task_id=UUID(str(r[1])),type=r[2],data=r[3] if isinstance(r[3],dict) else json.loads(r[3])) for r in rows]

    def audit(self, task_id: UUID|None=None) -> list[dict]:
        query="SELECT audit_id,task_id,action,data_json,created_at FROM audit_log"; params=()
        if task_id is not None: query+=" WHERE task_id=%s"; params=(str(task_id),)
        rows=self.postgres.execute(query+" ORDER BY created_at",params)
        return [{"audit_id":str(r[0]),"task_id":str(r[1]) if r[1] else None,"action":r[2],"data":r[3] if isinstance(r[3],dict) else json.loads(r[3]),"created_at":r[4].isoformat() if hasattr(r[4],"isoformat") else str(r[4])} for r in rows]

    def scheduler_status(self) -> dict[str,object]:
        snapshot=self.scheduler.snapshot(); snapshot.update({"worker_id":self.worker_id,"persistence":"postgresql"}); return snapshot

    def pause(self, task_id: UUID) -> Task|None:
        task=self.get(task_id)
        if task is None:return None
        if task.status in {TaskStatus.SUCCEEDED,TaskStatus.FAILED,TaskStatus.BLOCKED,TaskStatus.CANCELLED}:raise ValueError("task is already terminal")
        self.state_store.request_pause(task_id); task.status=TaskStatus.PAUSED; self._persist_task(task); self.runtime._event(task,"task.pause_requested",{"task_id":str(task_id)}); self._persist_events(task_id); return task

    def resume(self, task_id: UUID) -> Task|None:
        task=self.get(task_id)
        if task is None:return None
        if task.status!=TaskStatus.PAUSED:raise ValueError("task is not paused")
        if self.state_store.load(task_id) is None:raise ValueError("no persisted agent state exists for task")
        self.state_store.clear_pause(task_id); task.error=None; future=self._submit(task)
        try:result=future.result()
        finally:self._forget_future(task.task_id)
        self._persist_task(result); self._persist_events(result.task_id); return result

    def cancel(self, task_id: UUID) -> Task|None:
        task=self.get(task_id)
        if task is None:return None
        if task.status in {TaskStatus.SUCCEEDED,TaskStatus.FAILED,TaskStatus.BLOCKED,TaskStatus.CANCELLED}:return task
        self.state_store.request_cancel(task_id)
        with self._future_lock:future=self._futures.get(task_id)
        if future is not None and future.cancel():self.runtime._event(task,"task.cancelled",{"queued":True})
        else:self.runtime._event(task,"task.cancel_requested",{"running":True})
        task.status=TaskStatus.CANCELLED; self._persist_task(task); self._persist_events(task_id); return task


class _PostgresLeaseAdapter:
    def __init__(self,persistence:DistributedTaskPersistence):self.persistence=persistence
    def acquire(self,task_id:str,worker_id:str,lease_seconds:float):
        token=self.persistence.acquire_lease(task_id,worker_id,lease_seconds)
        if token is None:raise RuntimeError("task is already leased by another worker")
        return token
    def heartbeat(self,task_id:str,worker_id:str,token:str,lease_seconds:float):return self.persistence.heartbeat_lease(task_id,worker_id,token,lease_seconds)
    def release(self,task_id:str,worker_id:str,token:str):return self.persistence.release_lease(task_id,worker_id,token)
    def get(self,task_id:str):
        rows=self.persistence.store.execute("SELECT worker_id,lease_token,expires_at FROM worker_leases WHERE task_id=%s",(task_id,))
        if not rows:return None
        worker,token,expires=rows[0]
        now=datetime.now(timezone.utc)
        return {"worker_id":worker,"lease_token":token,"expired":expires<=now}

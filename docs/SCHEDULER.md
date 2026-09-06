# AETHON Scheduler

**Milestone:** Step 14E — Advanced Execution Scheduler + Concurrent Agent Tasks

## Goal

Move AETHON from a single bounded runtime to controlled concurrent execution without weakening safety, verification, or durable agent checkpoints.

## Current architecture

```text
Task request
    ↓
Priority admission
    ↓
Dependency gating
    ↓
Resource quota admission
    ↓
Bounded worker pool
 ┌─────────┬─────────┬─────────┐
 Agent #1  Agent #2  Agent #3  ...
 └─────────┴─────────┴─────────┘
    ↓
AgentRuntime checkpoints
    ↓
Verification + recovery
```

## Scheduling guarantees

- `AETHON_MAX_CONCURRENT_TASKS` bounds active workers; default is 4.
- `AETHON_MAX_QUEUED_TASKS` provides a hard queue bound; default is 100.
- Priorities range from 1 to 10; lower numeric values run first.
- Equal effective priority is FIFO.
- Priority aging prevents long-waiting low-priority work from starving indefinitely.
- Dependencies must complete successfully before dependent work is admitted.
- Independent work can bypass a blocked dependency.
- Resource quotas prevent overcommit of declared resources such as GPU slots.
- Invalid or oversized resource requests fail at admission.
- Scheduler failures propagate to the normal task recovery path.

## Fairness model

Each queued item records its monotonic submission time. Its effective priority is:

```text
max(1, base_priority - floor(wait_time / aging_interval))
```

The default aging interval is 30 seconds and can be changed with `AETHON_SCHEDULER_AGING_SECONDS`.

This is intentionally a bounded aging policy, not a claim of strict real-time fairness.

## Durability boundary

The scheduler is currently an **in-process** concurrency layer. Task records and agent checkpoints are durable, but the scheduler's in-memory queue and dependency futures are not a distributed durable queue.

Therefore:

- a running agent can use durable checkpoint recovery after restart;
- queued in-memory scheduler work is not a guaranteed restart-survivable queue;
- multiple service replicas must not share this scheduler as if it were a distributed coordinator.

A future distributed scheduler may move queue ownership, dependency state, resource leases, worker heartbeats, and fairness state into PostgreSQL/Redis or another durable coordination layer while preserving the same task and checkpoint contracts.

## Observability

`GET /v1/scheduler` exposes current queued/active counts, worker capacity, queue capacity, fairness interval, and resource usage. Task events and audit records remain the source of truth for execution history.

## Safety boundary

Concurrency does not grant authorization. Every privileged tool action still passes through the Safety Kernel. Model output is never itself an authorization decision.

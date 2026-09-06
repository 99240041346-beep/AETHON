# AETHON Master Blueprint

## Vision

**AETHON — Think. Create. Act.**

Build a highly capable general-purpose AI agent that can understand goals, reason about complex problems, plan long-running tasks, use authorized tools, browse the web, work with files and code, remember useful project context, learn legitimate skills, and eventually interact with authorized physical systems.

AETHON is a system/platform, not initially a claim of a new foundation model.

## Core loop

`Observe → Understand → Reason → Plan → Act → Verify → Learn`

## AETHON-0 objective

Build the smallest genuinely useful agent that can:

1. Accept a natural-language goal.
2. Convert the goal into a structured task.
3. Plan a bounded sequence of actions.
4. Select authorized tools.
5. Execute tools safely.
6. Observe outputs.
7. Verify the result.
8. Recover or re-plan when appropriate.
9. Store useful project state.
10. Return a clear result to the user.

## Major programs

### Program A — Digital Agent
- Phase 0: Product and architecture
- Phase 1: AETHON-0 foundation
- Phase 2: Tool system
- Phase 3: Browser agent
- Phase 4: Computer use
- Phase 5: Software engineering agent

### Program B — Intelligence
- Phase 6: Memory
- Phase 7: Multimodal
- Phase 8: World model
- Phase 9: Skill learning

### Program C — Safety and Models
- Phase 10: Safety Kernel
- Phase 11: Model research
- Phase 12: AETHON model family

### Program D — Physical and Production
- Phase 13: IoT/robotics
- Phase 14: Production platform

## Competitive principle

AETHON will not claim superiority without evidence. Capability claims must be backed by reproducible evaluations such as task success, reasoning accuracy, coding performance, tool-use reliability, browser completion, memory retrieval, safety violation rate, latency, and cost.

## Initial technology direction

- Web: Next.js, React, TypeScript
- API and agent runtime: Python, FastAPI
- Validation: Pydantic
- Database: PostgreSQL
- Vector retrieval: PostgreSQL/pgvector
- Transient state and queues: Redis when required
- Containers: Docker
- Tests: Pytest and Playwright
- Source control: Git/GitHub

Technology choices remain subject to implementation evidence and may be changed through documented architecture decisions.

## Repository philosophy

Prefer a modular monorepo with clear boundaries between UI, API, orchestration, tools, memory, security, evaluation, and model infrastructure. Do not introduce distributed-system complexity before workload justifies it.

## Security principle

The AI model never receives unrestricted authority. Important actions pass through identity, authorization, risk, policy, sandboxing, and approval controls before execution.

## Definition of progress

AETHON improves when a new version demonstrates measurable gains without unacceptable regressions in safety, reliability, latency, or cost.

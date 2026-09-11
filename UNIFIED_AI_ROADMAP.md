# AETHON / ASTRA — Unified AI Roadmap

This roadmap unifies the assistant, autonomous-agent, and operating-layer goals without creating a second product or replacing working AETHON modules.

## Current baseline

- Existing AETHON assistant/orchestration, memory, task lifecycle, safety gate, Android capability registry, Accessibility UI observation, command transport, workflow recovery, and CI are retained.
- `AETHON_SYSTEM_AUDIT.md` is the architectural source of truth for the existing implementation.
- The current branch is the integration line for incremental delivery.
- Capabilities are exposed through a single discovery registry and unavailable integrations are reported as unavailable rather than simulated.

## Delivery order

### Phase 1 — Foundation and security
- Unified capability registry
- Owner-scoped tool execution
- Production configuration validation
- Durable PostgreSQL path without silent downgrade
- Request/task/tool audit correlation
- Consistent error envelopes

### Phase 2 — Unified conversation
- Conversation/session/message API model
- Streaming response transport (SSE)
- Chat search, rename, archive, delete
- Attachments and artifact references
- Regenerate/edit/continue/stop semantics

### Phase 3 — Model router
- Provider abstraction
- Fast/general/reasoning/coding/vision model roles
- Provider health and bounded retry
- Context/cost/latency-aware routing
- Speech and image provider adapters

### Phase 4 — Tool engine
- Full ToolSpec metadata: schemas, risk, timeout, retries, auth and audit policy
- Central registration and capability discovery
- Execution envelopes and verification hooks
- Web search/fetch, files, data, code sandbox, GitHub, deployment and notifications

### Phase 5 — Agent runtime
- General, research, coding, browser, data, file, vision, document, design, DevOps, Android, computer, security and automation agents
- Bounded plans and step budgets
- Pause/resume/cancel/retry
- Re-planning and verification
- Human approval gates

### Phase 6 — Memory and projects
- Conversation/project/task memory scopes
- Searchable preference and project memory
- Privacy/deletion controls
- Projects containing conversations, files, instructions, memory, tasks, agents, GitHub and deployments

### Phase 7 — Multimodal intelligence
- PDF/DOCX/PPTX/XLSX/CSV/image/audio/video/code ingestion
- Data analysis and visualization
- Document generation and validation
- Image generation/editing/vision

### Phase 8 — Web and coding factory
- Research pipeline with source validation and citations
- Repository inspection/patch/test/verify workflow
- GitHub branches, commits, PRs and workflow status
- Idea → requirements → design → code → database → API → tests → deploy → monitor

### Phase 9 — Local computer and Android operating layer
- Authenticated local agent
- Files/browser/terminal/application capabilities behind a registry
- Android bridge and device center
- ADB-first Windows architecture
- Accessibility semantic observation/actions
- Device result verification

### Phase 10 — Automation and voice
- One-time/recurring/conditional tasks
- Monitoring and notifications
- Speech input/output
- Interruption/turn-taking where supported

### Phase 11 — Production hardening
- Prompt-injection trust boundaries
- SSRF/file/dependency controls
- Sandboxed generated code
- Rate limits, caching, queues and connection pooling
- Full audit/tracing and security events
- End-to-end regression suite

### Phase 12 — Production release
- Staging deployment
- Environment validation
- Health/readiness checks
- Smoke tests
- Android release builds
- Performance/cost verification
- Disaster recovery and operational runbooks

## Non-negotiable definition of done

A feature is complete only when its implementation exists, its capability is accurately discoverable, permissions are enforced, failures are observable, important actions are verified, and regression tests pass. No fake controls, fabricated results, unrestricted model-generated host commands, secret leakage, or silent security bypasses.

## Continuous execution policy

Work proceeds from the highest-value incomplete phase to the next without waiting for a manual "next" instruction. Existing functionality is patched and extended rather than replaced. When an external integration is unavailable, the platform records the missing dependency and keeps the rest of the system operational.

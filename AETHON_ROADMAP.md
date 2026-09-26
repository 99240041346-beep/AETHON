# AETHON Roadmap

## Product north star
AETHON is a personal AI operating layer: `Understand -> Plan -> Execute -> Verify -> Report` across cloud AI, files, web, code, GitHub, deployment, Android and an authorized local agent.

## Phase 1 — Stabilize existing system
- [x] Preserve existing Android UI and modules.
- [x] Keep safety kernel, owner scoping and bounded Android control.
- [x] Add public HTTPS client path.
- [x] Add system audit.
- [ ] Provision isolated production PostgreSQL for AETHON.
- [ ] Make `/ready` a required deployment gate.
- [ ] Complete production auth/session lifecycle.
- [ ] Add API rate limits and security headers.

## Phase 2 — Core AI
- [x] Model provider abstraction.
- [x] Configurable Responses API provider.
- [ ] Production model configuration and secret validation.
- [ ] Streaming SSE/WebSocket responses.
- [ ] Conversation editing/regeneration/export.
- [ ] Multimodal input contract for image/document/audio/video.
- [ ] Task-aware model routing.

## Phase 3 — Tool system
- [ ] Canonical typed ToolSpec and ExecutionEnvelope.
- [ ] Tool permissions/risk/timeout/retry metadata.
- [ ] Per-user and per-task budgets.
- [ ] Tool result validation.
- [ ] Central audit events.
- [ ] Capability discovery endpoint/UI.

## Phase 4 — Agent runtime
- [ ] Plan graph with bounded step count/time/cost/tool calls.
- [ ] Planner/executor/verifier separation.
- [ ] Approval checkpoints.
- [ ] Pause/resume/cancel/retry.
- [ ] Alternative-tool recovery.
- [ ] Persistent agent-run traces.

## Phase 5 — Memory
- [x] Owner-scoped memory APIs.
- [ ] Conversation summarization.
- [ ] Project memory.
- [ ] Task memory.
- [ ] Explicit user preference memory controls.
- [ ] Secret detection/redaction before memory writes.
- [ ] Retention and deletion policies.

## Phase 6 — Web / Research
- [ ] Production web-search connector.
- [ ] Source extraction and quality scoring.
- [ ] Cross-source synthesis.
- [ ] Citation objects tied to retrieved sources.
- [ ] Prompt-injection isolation for external pages.

## Phase 7 — Coding Agent
- [ ] Repository inspection tool.
- [ ] Safe patch workflow.
- [ ] Sandboxed Python/JS/TS execution.
- [ ] Build/test/lint orchestration.
- [ ] Dependency/security scanning.
- [ ] Artifact packaging.

## Phase 8 — Local Computer Agent
- [ ] Secure local-agent enrollment.
- [ ] Short-lived credentials.
- [ ] Capability-scoped filesystem/app/browser operations.
- [ ] Explicit shell policy with sandboxing.
- [ ] Local audit and offline queue.
- [ ] Device health/heartbeat.

## Phase 9 — Android / ADB Agent
- [x] Android bounded command transport.
- [x] Semantic Accessibility observation/action layer.
- [x] Workflow pause/resume/cancel/retry foundation.
- [ ] Production Android enrollment UX.
- [ ] ADB local-agent protocol.
- [ ] Screenshot/file/log/diagnostic capabilities through allowlists.
- [ ] End-to-end real-device test suite.

## Phase 10 — Automation
- [ ] One-time schedules.
- [ ] Recurring schedules and time zones.
- [ ] Background worker queue.
- [ ] Approval notifications.
- [ ] Failure/retry notifications.
- [ ] Device online/offline notifications.

## Phase 11 — Security hardening
- [ ] Threat model and security test suite.
- [ ] SSRF defenses.
- [ ] Upload validation and malware-aware isolation.
- [ ] Sandbox escape tests.
- [ ] Prompt-injection regression corpus.
- [ ] Rate limiting and abuse controls.
- [ ] Secret scanning/redaction.
- [ ] Production dependency and container scanning.

## Phase 12 — Product completion
- [ ] Projects/workspaces.
- [ ] Files/artifacts UI.
- [ ] Agents UI.
- [ ] Tasks/automations UI.
- [ ] Devices UI.
- [ ] Sources/activity panel.
- [ ] Developer observability console.
- [ ] Usage/cost dashboard.
- [ ] Voice conversation polish and interruption.

## Definition of done
A feature is not complete when code exists. It is complete only when:
1. Existing behavior is preserved.
2. Unit/integration tests pass.
3. Security policy is enforced.
4. Build passes.
5. API readiness passes.
6. Smoke tests pass.
7. Failure behavior is verified.
8. Documentation is updated.
9. The user-facing UI reports real state rather than placeholders.

## Continuous execution policy
AETHON development should proceed in small verified increments. Never replace the repository wholesale. Prefer additive modules and narrow patches. If an external capability is not configured, expose its real unavailable state instead of simulating success.

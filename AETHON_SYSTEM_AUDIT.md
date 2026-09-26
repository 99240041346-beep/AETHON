# AETHON System Audit

Date: 2026-09-11
Branch: `feat/android-ui-observation-20260911`

## 1. Current architecture
AETHON is an existing Python/FastAPI backend plus Android client. The backend already separates authentication, safety, model routing, memory, tasks, assistant orchestration, device gateway, Android command transport and language/voice APIs. Android contains a bounded local executor and Accessibility-based UI observation/control layer.

Current high-level flow:

`User -> Android UI -> HTTPS API -> auth -> assistant orchestrator/model router -> safety/tool/device layers -> durable task/command state -> verified result`

## 2. Existing features
- Conversational assistant endpoint with language detection.
- Task creation, status, plan, events, audit, pause/resume/cancel.
- Memory write/search/maintenance/delete APIs.
- Model router with deterministic fallback and configurable external provider.
- Safety kernel and execution authorization gate.
- Device gateway and authenticated Android command transport.
- Bounded Android UI observation and semantic actions.
- Android workflows with pause/resume/cancel and bounded retries.
- Voice API and Android speech recognition/TTS integration.
- Personal AI command-center Android dashboard.

## 3. Existing frontend
The repository contains an Android application under `android/app`. Existing UI has been preserved and extended with a personal AI command center. The Android main activity now supports public HTTPS configuration, conversation, voice control, TTS and device-link controls.

## 4. Existing backend
The API entry point is `services/api/app/main.py`. It registers voice, device, assistant, language and Android command-transport routers. Persistence selection is explicit: PostgreSQL is used when `AETHON_DATABASE_URL` is configured; otherwise the task store can operate locally. The `/ready` endpoint reports persistence readiness.

## 5. Existing database
PostgreSQL support exists for durable task/device-command workflows and migrations. The production cloud deployment still requires an AETHON-specific `AETHON_DATABASE_URL`; an unrelated existing database must not be silently reused. Local stores remain useful for development/tests.

## 6. Existing APIs
Notable routes include:
- `/health`, `/ready`
- `/v1/model/health`
- `/v1/tools`, `/v1/tools/execute`
- `/v1/memory/*`
- `/v1/tasks/*`
- `/v1/assistant/respond`
- `/v1/assistant/device-action`
- `/v1/assistant/device-workflow`
- `/v1/assistant/android-workflows/*`
- assistant session/history APIs
- voice, language, device gateway and Android command transport APIs.

## 7. Existing agent system
The current implementation has an assistant orchestrator plus bounded Android workflow planning and recovery. A full general-purpose multi-agent runtime, browser agent, research agent, coding agent and deployment agent are not yet complete as first-class production modules.

## 8. Existing Android integration
Android uses supported platform APIs and AccessibilityService for semantic UI observation/actions. Local device capabilities include bounded flashlight, volume, media, battery/device information, app launch and screen/UI operations. Actions are allowlisted and verification-aware. No root, arbitrary shell or unrestricted coordinate injection is part of the intended architecture.

## 9. Existing local-agent implementation
The repository direction is ADB-first: cloud orchestration must not depend on Windows `adb.exe`; a local agent is the correct place for ADB and local-computer capabilities. A complete production local-computer agent still needs a hardened capability protocol, enrollment, encrypted transport, policy enforcement and lifecycle management.

## 10. Existing authentication
Backend authorization uses bearer credentials and owner scoping. Device commands are owner/device scoped. The platform still needs a complete public account lifecycle (registration, secure password hashing, verification/reset and optional OAuth) before being considered a general production identity system.

## 11. Existing tests
API and Android CI workflows exist. The project has extensive regression coverage around task state, memory, safety, Android UI state, command transport and workflow recovery. Android CI builds a debug APK. The remaining roadmap requires broader end-to-end, security and real-device coverage.

## 12. Existing deployment
A Render web service exists for AETHON with HTTPS and automatic deployment. Production readiness is currently conditional on required environment configuration, especially durable PostgreSQL and a real model provider key. The public service must be health/ready/smoke-tested before being called production-ready.

## 13. Broken / incomplete features
1. Public cloud persistence is not yet independently provisioned for AETHON.
2. The assistant can fall back to deterministic responses; a production model key is still configuration-dependent.
3. Web research is not yet a complete citation-safe first-class research agent.
4. Full coding sandbox is not yet implemented.
5. Full browser agent is not yet implemented.
6. Full file/artifact pipeline is not yet unified.
7. General GitHub/deployment agents are not yet unified behind one tool registry.
8. Account lifecycle and production secret management need completion.
9. Physical Android testing cannot be performed remotely by the cloud; it requires the user's device/agent.
10. Voice quality is dependent on the TTS voices available on the device; the app can prefer a deeper/female voice but cannot manufacture a voice that Android does not provide.

## 14. Security issues / risks to address
- Keep model-generated tool calls behind schema validation and the safety gate.
- Never expose unrestricted shell/ADB through a public endpoint.
- Enforce owner/device binding on every command.
- Add rate limits and abuse protection to public endpoints.
- Add SSRF protections to web/browser tools.
- Sandbox code execution with strict CPU, memory, process, filesystem and network limits.
- Validate uploads and isolate untrusted documents/code.
- Treat web/document/code content as untrusted instructions.
- Keep secrets out of prompts, logs and ordinary memory.
- Use short-lived device credentials where practical.

## 15. Missing capabilities
- Unified Tool Registry v2 with typed schemas and execution envelopes.
- Agent runtime with bounded plans and budgets.
- Streaming chat/event protocol.
- Production web research + citations.
- Multimodal file/vision pipeline.
- Sandboxed coding execution.
- Browser/local-computer agent.
- GitHub and deployment agents.
- Unified project workspace model.
- Scheduler/notifications integration.
- Full artifact generation/validation pipeline.
- Cost/usage telemetry.
- Developer observability console.

## 16. Dependency issues
Dependencies need continuous CI auditing. External model, browser, image and speech integrations must be optional/configurable rather than required for deterministic CI. Production-only integrations must fail clearly when configuration is missing.

## 17. Technical debt
- Some assistant behavior is still centralized in `assistant_api.py` rather than a fully separated agent runtime.
- Persistence implementations are split between legacy/local and PostgreSQL paths.
- Tool definitions and execution need one canonical registry/envelope.
- Streaming and event transport are not yet a single cross-platform abstraction.
- Production configuration needs a documented environment contract.

## 18. Recommended architecture
Use a control-plane/data-plane split:

**Control plane:** auth, projects, conversations, plans, permissions, memory, task state, audit and observability.

**Agent runtime:** planner -> policy -> tool registry -> executor -> verifier -> recovery.

**Execution planes:** cloud-safe tools, sandbox workers, browser worker, local computer agent and Android agent.

Every execution should use:
`intent -> plan -> policy -> typed tool call -> execution -> verification -> audit -> user result`.

## 19. Prioritized implementation plan
### P0 — Stabilize
Production DB, environment validation, CI, health/readiness, authentication hardening, regression tests.

### P1 — Core AI
Real model router, streaming responses, conversation persistence, multimodal input contract.

### P2 — Tool/agent runtime
Unified registry, budgets, permissions, tool envelopes, planner/executor/verifier and recovery.

### P3 — Capability agents
Research, coding sandbox, files/data, browser, GitHub, deployment and Android/local agents.

### P4 — Product
Projects, automations, notifications, artifacts, developer console, usage/cost telemetry.

### P5 — Hardening
Prompt-injection defenses, SSRF, sandbox security, rate limits, device enrollment, E2E tests and production smoke tests.

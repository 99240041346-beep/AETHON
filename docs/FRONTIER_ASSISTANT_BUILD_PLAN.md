# AETHON Frontier Assistant Build Plan

## Goal

Build AETHON as a Telugu-first personal agent that combines the existing AETHON planning, recovery, memory, safety, browser, computer, software-engineering, voice, model-routing, distributed, and device foundations into one user-facing assistant.

The target capability envelope is informed by the current GPT-6 Astra feature set: complex reasoning, multistep work, computer use, browsing, software engineering, research, science/data workflows, document creation, multimodal inputs, adaptive task steering, and strong safety boundaries. OpenAI describes Astra as supporting web search, file search, image generation, code interpreter, hosted shell, computer use, MCP, structured outputs, streaming, and multi-agent orchestration. citeturn1search2turn1search3

## Build sequence

### 30A — Assistant control plane
- unified `/v1/assistant/respond` contract
- intent/mode routing
- session/project context
- bounded autonomy declaration
- existing AgentRuntime integration
- capability discovery

### 30B — Realtime voice
- `Hey Buddy` wake state
- streaming Telugu STT
- interruption/barge-in
- streaming TTS
- response cancellation
- realtime session transport

### 30C — Multimodal workspace
- images
- screenshots
- camera frames
- PDFs/documents
- audio
- video metadata and bounded analysis
- unified attachment references

### 30D — Action adapters
- Android device capabilities
- Windows computer agent
- browser agent
- software-engineering workspace
- files/artifacts
- calendar/email adapters
- telephony adapter with explicit user authorization
- IoT adapters

### 30E — Frontier model orchestration
- capability-aware model routing
- reasoning effort selection
- async tool calls
- mid-task steering
- model fallback
- cost/latency budgets
- provider-neutral contracts

### 30F — Proactive assistant
- reminders
- scheduled tasks
- follow-ups
- event-triggered workflows
- notification summaries
- user-configurable autonomy policies

### 30G — Memory and personalization
- user profile
- preferences
- contacts
- project memory
- episodic task history
- semantic knowledge
- retrieval ranking
- forgetting/retention policies
- strict owner/project isolation

### 30H — Artifact studio
- DOCX
- PDF
- PPTX
- XLSX
- charts
- code repositories
- websites/apps
- generated media
- downloadable verified artifacts

### 30I — Evaluation and release
- task success benchmarks
- Telugu benchmark
- browser/computer benchmark
- coding benchmark
- multimodal benchmark
- safety boundary benchmark
- latency/cost benchmark
- regression suite
- Android GitHub Actions APK gate

## Safety requirement

Capability parity does not mean removing safeguards. Every external side effect remains behind SafetyKernel, SafetyExecutionGate, explicit approval where required, authenticated adapters, bounded execution, verification, and audit. Frontier cyber capability is treated as a high-risk domain and is restricted to defensive, authorized workflows.

## Success criterion

AETHON is not declared "better than Astra" by marketing language. It is measured capability-by-capability and must demonstrate improved task completion, Telugu interaction, reliability, safety, personalization, and execution quality on its own evaluation suite before claiming superiority.

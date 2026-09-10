# AETHON Frontier Assistant Capability Matrix

AETHON is being developed as a Telugu-first, multimodal personal agent with bounded autonomy. This matrix turns the requested "ChatGPT + GPT-6 Astra class" target into engineering capabilities that can be implemented and measured.

## Capability groups

| Group | Target capability | AETHON foundation | Adapter / next implementation |
|---|---|---|---|
| Conversation | Telugu + Telugu-English dialogue | Voice API + model router | Streaming realtime conversation |
| Wake word | "Hey Buddy" activation | Android voice client | On-device wake-word engine |
| Reasoning | Goal decomposition, planning, replanning | Agent Brain / Task Graph / Recovery | Frontier model routing |
| Long tasks | Bounded autonomous execution | AgentRuntime + execution budgets | Async worker orchestration |
| Memory | Working, project, episodic, learned context | Memory repository + learning | Session timeline + retrieval ranking |
| Web | Search/fetch/browser workflows | Browser agent + web runtime | Authenticated browser session adapter |
| Computer | Desktop interaction | Computer agent foundation | Windows device-agent transport |
| Coding | Code generation/debug/build/test/review | Software engineering agent | Sandboxed workspace execution |
| Documents | Read/write/summarize/transform files | File/document foundations | Artifact service |
| Data | CSV/spreadsheets/analysis | Evaluation/data foundations | Sandboxed data-analysis worker |
| Vision | Image/screenshot understanding | Multimodal foundations | Android camera/screen transport |
| Voice | STT/TTS and Telugu responses | Android voice client | Realtime audio transport |
| Android | Device capabilities and notifications | Device Gateway | Authenticated Android capability adapters |
| IoT | Physical-world operations | Physical Gateway policy | Authenticated hardware adapters |
| Email | Draft/send/search | Tool/approval architecture | OAuth mail adapter |
| Calendar | Read/create/update events | Task/approval architecture | OAuth calendar adapter |
| Phone calls | Natural outbound calls + summaries | Voice architecture | Explicit telephony provider adapter |
| Research | Web research + evidence synthesis | Browser + reasoning | Source/evidence pipeline |
| Science | Data/math/science workflows | Reasoning + data foundations | Scientific tool adapters |
| Artifacts | PPTX/DOCX/XLSX/PDF generation | Existing artifact ecosystem | Unified artifact workspace |
| Collaboration | Mid-task steering and resumability | Durable AgentRuntime state | Streaming control channel |
| Safety | Fail-closed authorization | SafetyKernel + SafetyExecutionGate | Per-adapter policy contracts |
| Verification | Verify before claiming completion | Verifier + WebAwareVerifier | Domain-specific verifiers |
| Audit | Explain what was attempted and verified | Event/audit lifecycle | User-facing activity timeline |

## Non-negotiable boundary

AETHON must never claim that an external action happened unless an authorized adapter actually performed it and a verifier observed success. Models, memories, plans, routing decisions, and learned experience never grant authorization.

## Frontier benchmark plan

AETHON should measure itself rather than use marketing claims as a proxy for capability. The evaluation lab will track:

- task success rate
- verification accuracy
- unauthorized-action rate
- recovery success rate
- tool-call accuracy
- browser/computer completion rate
- coding build/test success
- research citation/evidence quality
- Telugu speech recognition quality
- Telugu response quality
- latency and token efficiency
- user intervention rate
- memory retrieval precision

The target is to progressively close measurable gaps against frontier systems, not to claim parity without evidence.

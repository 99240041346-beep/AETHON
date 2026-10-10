# AETHON

**Think. Create. Act.**

AETHON is a long-term engineering project for building a secure, measurable, general-purpose AI agent platform.

## Engineering principle

AETHON is developed incrementally. We measure capabilities, compare them against defined baselines, identify weaknesses, improve the system, and regression-test every release.

## AETHON-0

The first milestone is a verified tool-using agent with:

- Web interface
- API
- Agent orchestration
- Model routing
- Planning
- Authorized tools
- Basic memory
- Verification
- Safety controls
- Audit logging
- Evaluation

## Repository

See `docs/MASTER_BLUEPRINT.md` for the product and research blueprint and `docs/ARCHITECTURE.md` for the initial technical architecture.

## Status

Phase 0 — Foundation

Milestone 0.1 — Repository and architecture foundation


## AETHON web console

The API serves the browser control console at `/`. It provides Assistant chat, browser voice input/output, file attachments, autonomous agents, the AI Factory lifecycle, device-control visibility, projects, research, capabilities, settings, and API documentation. The Android AETHON app remains the primary device-control hub.

### Local test

From `services/api`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`. Configure `AETHON_MODEL_API_KEY` (and optionally `AETHON_MODEL_PROVIDER=openai`) for model-backed generation; without it, bounded local intelligence remains available.

### Use Ollama as AETHON's AI brain (local model)

1. Install Ollama from [ollama.com/download](https://ollama.com/download) on the same computer that runs the AETHON API.
2. In a terminal, download a starter model: `ollama pull llama3.2:3b`.
3. Confirm Ollama is running with `ollama list`.
4. In the same terminal used to start AETHON, set the model environment variables.

**Windows PowerShell:**

```powershell
$env:AETHON_MODEL_PROVIDER = "ollama"
$env:AETHON_MODEL_BASE_URL = "http://127.0.0.1:11434"
$env:AETHON_MODEL_NAME = "llama3.2:3b"
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**macOS/Linux:**

```bash
export AETHON_MODEL_PROVIDER=ollama
export AETHON_MODEL_BASE_URL=http://127.0.0.1:11434
export AETHON_MODEL_NAME=llama3.2:3b
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`. Ollama runs the model locally; the first reply can take longer while the model loads. AETHON uses Ollama's native `/api/chat` API and `/api/tags` health check.

**Important for the Render deployment:** `127.0.0.1:11434` on Render means the Render container itself, not your laptop. Setting these variables on Render alone will not connect it to Ollama running on your PC. For the hosted AETHON site to use Ollama, Ollama must be running on a reachable server/private network endpoint and `AETHON_MODEL_BASE_URL` must point to that endpoint; do not expose Ollama publicly without authentication and network restrictions. Local installation is the quickest way to give your local AETHON instance a real model brain.

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


## ASTRA web console

The API serves the browser control console at `/`. It provides Assistant chat, browser voice input/output, file attachments, autonomous agents, the AI Factory lifecycle, device-control visibility, projects, research, capabilities, settings, and API documentation. The Android ASTRA app remains the primary device-control hub.

### Local test

From `services/api`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`. Configure `AETHON_MODEL_API_KEY` (and optionally `AETHON_MODEL_PROVIDER=openai`) for model-backed generation; without it, bounded local intelligence remains available.

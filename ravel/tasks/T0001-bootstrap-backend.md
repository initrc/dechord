---
id: T0001
title: Bootstrap backend project
status: new
dependencies: []
---

# Scope

- Set up a `uv`-managed Python project for the FastAPI backend with dependencies `fastapi[standard]`, `pydantic`, `madmom` (which pulls `torch`).
- Create a minimal FastAPI app at `backend/main.py` with a `/health` endpoint and CORSMiddleware enabled (the Next.js dev server runs on a different port).
- Verify madmom installs cleanly on macOS and that the chosen chord recognizer processor can be instantiated without error.

# Acceptance

- `uv sync` installs all dependencies without errors on the M1 target machine.
- `uv run uvicorn main:app --reload` (run inside `backend/`) starts the server.
- `GET /health` returns 200.
- A Python one-liner imports `madmom.features.chords.DeepChromaChordRecognitionProcessor` and constructs it without error.
- The chosen `pyproject.toml` linter (ruff default config) passes on the empty state.

# Implementation Notes

- Proposed repo layout: project code at the repo root — `/Users/davidshi/code/dechord/backend/` for the FastAPI service, `/Users/davidshi/code/dechord/frontend/` for the Next.js app. The existing `ravel/` subtree continues to hold design docs and tasks. Adjust if a different layout is preferred.
- `fastapi[standard]` pulls `uvicorn` implicitly; do not declare `uvicorn` separately.
- madmom pulls `torch` transitively. On M1 torch runs on CPU; CUDA users get GPU automatically. No code-side device selection in v1.
- `ffmpeg` must be on PATH — it is used by later tasks to normalize uploads. Document this as a prereq in the backend README or a setup script; do not bundle ffmpeg.
- CORS middleware should allow the Next.js dev origin (`http://localhost:3000`) for development. Permit all origins for v1 (local-only tool).
- Reference: `ravel/docs/design-v1.md` Backend section.
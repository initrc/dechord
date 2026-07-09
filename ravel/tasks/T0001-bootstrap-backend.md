---
id: T0001
title: Bootstrap backend project
status: done
dependencies: []
---

# Scope

- Set up a `uv`-managed Python project (script-style, no `app/` package) for the FastAPI backend with dependencies `fastapi[standard]`, `pydantic`, and `madmom`.
- Create a minimal FastAPI app at `backend/main.py` with a `/health` endpoint and CORSMiddleware enabled for the Next.js dev origin (`http://localhost:3000`).
- Verify madmom installs cleanly on macOS (Python 3.13) and that `DeepChromaChordRecognitionProcessor` can be instantiated without error.
- Add a `backend/Makefile` with shortcuts (`dev`, `sync`, `lint`, `clean`) so the long `uv run uvicorn main:app --reload` invocation isn't typed by hand.

# Acceptance

- `uv sync` installs all dependencies without errors on the M1 target machine.
- `uv run uvicorn main:app --reload` (run inside `backend/`) starts the server; equivalently `make dev` from `backend/`.
- `GET /health` returns 200.
- A Python one-liner imports `madmom.features.chords.DeepChromaChordRecognitionProcessor` and constructs it without error.
- `uv run ruff check .` passes.

# Implementation Notes

- Repo layout: `backend/` for the FastAPI service, `frontend/` for the Next.js app, `ravel/` for design docs and tasks.
- `uv init --app` produced a script-style project: `main.py` at `backend/` root, an `app` object (a `FastAPI()` instance). Do **not** restructure into `app/` — `fastapi dev` (the CLI) defaults to `app`, but this project uses `uv run uvicorn main:app` which matches the flat layout.
- `fastapi[standard]` pulls `uvicorn` and `fastapi-cli` implicitly; do not declare `uvicorn` separately.
- **madmom and Python 3.13:** the last released madmom (0.16.1, 2018) is source-incompatible with Python >= 3.10 — it does `from collections import MutableSequence` (removed in 3.10) and imports `pkg_resources` (gone in setuptools >= 81). Fix: install madmom from the CPJKU/madmom `main` branch via `[tool.uv.sources]` in `backend/pyproject.toml`, with an explanatory comment. The `main` branch fixes both (`importlib.metadata`, `collections.abc`). Revisit once 0.17 is published to PyPI.
- **No torch:** madmom uses its own numpy-based neural-network stack, not pytorch. The v1 design doc's "madmom pulls `torch`" note is inaccurate; no torch dependency was added and no code-side device selection is needed.
- `ffmpeg` must be on PATH — used by later tasks to normalize uploads. Documented as a prereq in `backend/README.md`; not bundled.
- CORS allows `http://localhost:3000` only (tightened from the original "permit all origins" suggestion — sufficient for local v1).
- `backend/Makefile` exposes `dev` (run uvicorn with reload), `sync`, `lint` (ruff), `clean`. Run from `backend/` where `main.py` lives. Targets are declared `.PHONY` since none produce files — `make` would otherwise skip a target if a same-named file/dir ever appeared.
- Reference: `ravel/docs/design-v1.md` Backend section.
# dechord backend

FastAPI service for chord progression recognition.

## Prerequisites

- Python >= 3.13, managed with [uv](https://docs.astral.sh/uv/).
- `ffmpeg` on `PATH` — used to normalize uploads to mono 44.1 kHz before
  recognition. Install via Homebrew: `brew install ffmpeg`.

## Setup

```sh
uv sync
```

## Run (dev)

```sh
uv run fastapi dev
```

The CLI auto-discovers `app/main.py` and the `app` object. (Equivalent explicit
form: `uv run uvicorn app.main:app --reload`.)

Server starts on http://localhost:8000. `GET /health` returns `{"status": "ok"}`.

## Test

```sh
uv run pytest
```

(Or `make test`.)

The Next.js dev server runs on a different port (3000); CORS is enabled for it.

## Notes

- Application code lives in the `app/` package (entrypoint `app.main:app`);
  tests under `tests/`.
- madmom is installed from the CPJKU/madmom `main` branch because the last
  release (0.16.1) is incompatible with Python 3.13. See `pyproject.toml`.
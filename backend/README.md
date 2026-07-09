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
uv run uvicorn main:app --reload
```

Server starts on http://localhost:8000. `GET /health` returns `{"status": "ok"}`.

The Next.js dev server runs on a different port (3000); CORS is enabled for it.

## Notes

- madmom is installed from the CPJKU/madmom `main` branch because the last
  release (0.16.1) is incompatible with Python 3.13. See `pyproject.toml`.
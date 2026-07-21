# Dechord

An audio tool for decoding chord progressions

Dechord takes music files and recognizes the chords with
[madmom](https://github.com/CPJKU/madmom), then stores the result so you can
replay the track, re-run recognition, or revisit the chords later. Play the
track back and the recognized chords sweep by in sync, so you can see where each
chord falls in the song and improvise over it.

Where traditional DAWs lay tracks out in one long horizontal strip, Dechord
wraps chords and the master waveform across multiple lines like sheet music
for easy reading.

![Dechord v1](https://github.com/initrc/dechord/blob/main/assets/dechord-v1.png)

## Architecture

Two services, run side by side in dev:

- **`backend/`** — FastAPI + Pydantic + stdlib `sqlite3`. Stores uploads
  content-hash addressed under `backend/library/`, runs chord recognition in a
  FastAPI `BackgroundTask`, and writes `chords.json` back to the library.
- **`frontend/`** — Next.js + React + shadcn/ui. Proxies API calls to the
  backend through a Next.js rewrite (`/api/:path*` → `http://localhost:8000`),
  so both share one origin and the backend ships without CORS.

Recognition is asynchronous: `POST /media` returns immediately with an id, the
frontend polls `GET /jobs/{id}` until the chord stage completes.

See [`ravel/docs/design-v1.md`](ravel/docs/design-v1.md) for the full design and
[`ravel/docs/recognizer-benchmark.md`](ravel/docs/recognizer-benchmark.md) for
the madmom-variant comparison that drove the recognizer choice.

## Prerequisites

- Python >= 3.13, managed with [uv](https://docs.astral.sh/uv/).
- Node.js + [pnpm](https://pnpm.io).
- `ffmpeg` on `PATH` — used to normalize uploads to mono 44.1 kHz before
  recognition. Install via Homebrew: `brew install ffmpeg`.

## Setup & run

Backend (http://localhost:8000):

```sh
uv sync                    # from backend/
uv run fastapi dev
```

Frontend (http://localhost:3000):

```sh
pnpm install               # from frontend/
pnpm dev
```

Open http://localhost:3000, upload a track, and wait for the row to flip to
`done` — then click through to the item view for the chord + waveform tracks.

## Quality gates

Backend, from `backend/`:

```sh
make lint        # ruff
make typecheck   # mypy (app + tests)
make test        # pytest
```

Frontend, from `frontend/`:

```sh
pnpm lint
pnpm typecheck
```

Per-package notes live in [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md).

## REST surface

| Method | Path                          | Purpose                                              |
| ------ | ----------------------------- | ---------------------------------------------------- |
| POST   | `/media`                      | Multipart upload; queues a recognition job.           |
| GET    | `/media`                      | List media items (powers the library list).          |
| GET    | `/media/{id}`                 | Full record incl. `chords` (the output contract).    |
| GET    | `/media/{id}/audio/source`    | Streams the original upload.                          |
| POST   | `/media/{id}/chords`           | Re-run recognition on an existing item.              |
| GET    | `/jobs/{id}`                   | Poll job status (`queued\|recognizing\|done\|failed`). |

Chord labels are JAMS-style (`C:maj`, `A:min`, `N`) over the maj/min/N
vocabulary that madmom emits; the frontend renders them as `C`, `Am`.

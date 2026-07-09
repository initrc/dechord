---
id: T0007
title: Implement library read endpoints
status: new
dependencies:
  - T0003
  - T0005
  - T0006
---

# Scope

- Implement the read-side endpoints per design-v1.md:
  - `GET /media` → list of `{ id, original_filename, uploaded_at, status, has_chords }`.
  - `GET /media/{id}` → full record including `audio` metadata and `chords` (the Output contract).
  - `GET /media/{id}/audio/source` → streams the stored original file with a correct Content-Type.
  - `POST /media/{id}/chords` → enqueues a re-recognition job on an existing media item and returns `{ job_id }`.

# Acceptance

- After uploading via `POST /media` and waiting for job completion (verify via `GET /jobs/{id}`), `GET /media` lists the item with `has_chords: true`.
- `GET /media/{id}` returns the full record matching the Output contract JSON shape (audio metadata + chords array).
- `GET /media/{id}/audio/source` streams the original file; the response Content-Type matches the extension (`audio/mpeg`, `audio/wav`, etc.).
- `GET /media/{id}` on an unknown id returns 404.
- `POST /media/{id}/chords` returns `{ job_id }` and starts a new recognition job; polling `GET /jobs/{job_id}` transitions through the same lifecycle as a fresh upload.
- Lint passes.

# Implementation Notes

- For streaming audio, use FastAPI's `StreamingResponse` or `FileResponse`. `FileResponse` auto-detects Content-Type from the file extension; prefer it for simplicity.
- `chords` should be read from `chords.json` (written by T0005) — read from disk on demand, or cache in memory keyed by media id. v1 simplest: read from disk on every request; caching is premature for a local single-user tool.
- `POST /media/{id}/chords` re-runs recognition on an existing item and overwrites `chords.json`. Set `media.status` back to `recognizing` here; T0006's job runner handles the rest.
- Reference: `ravel/docs/design-v1.md` Output contract, Endpoint surface.
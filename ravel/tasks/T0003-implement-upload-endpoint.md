---
id: T0003
title: Implement upload endpoint
status: done
dependencies:
  - T0002
---

# Scope

- Implement `POST /media` (multipart upload) per design-v1.md.
- Validate upload format and size (propose: 50 MB max; `mp3`, `wav`, `flac`, `m4a`).
- Compute the SHA-256 of the uploaded bytes; dedup if a media row with the same sha256 already exists (return the existing id, do not re-store or re-queue).
- Normalize the stored file to mono 44.1 kHz WAV via `ffmpeg` for downstream recognition; store the normalized WAV alongside the original.
- Create a `media` row in `queued` status and (in this task) mark it `done` immediately — queueing is wired in T0005/T0006. The endpoint here returns `{ id }`.

# Acceptance

- `POST /media` with a valid mp3 returns `{ id }` and 201, and stores the original plus a normalized WAV under `library/`.
- A second upload of the same byte-identical file returns the same `id` and does not create a new row or new files.
- An upload exceeding the size limit returns 413; an unsupported format returns 415.
- `GET /media/{id}/audio/source` (handled by T0007) will be able to stream the original file once T0007 lands; here, verify manually by file path lookup.
- Lint passes.

# Implementation Notes

- Use Pydantic models for the response (`MediaIdResponse { id: str }`).
- Original file path: `library/{sha256}.{ext}`. Normalized WAV path: `library/{sha256}/source.wav` (next to where `chords.json` will land in T0005).
- Preserve the user-supplied filename in `original_filename` — it is displayed in the frontend library list.
- `ffmpeg` invocation: `ffmpeg -i <input> -ac 1 -ar 44100 <output>.wav`. Stderr from ffmpeg should be captured for diagnostics.
- Open decision #1 in design-v1.md proposes the size/format limits; confirm before locking.
- Reference: `ravel/docs/design-v1.md` Backend section, Endpoint surface.

# Results

- Locked open decision #1 at the proposed values: **50 MB max**, formats
  **`mp3`, `wav`, `flac`, `m4a`** (definitions in `app/uploads.py`).
- New module `app/uploads.py` owns `ingest_upload()`: extension validation
  (415), chunked stream + size enforcement (413, aborts at the limit rather
  than buffering the whole upload), SHA-256 of the bytes, dedup lookup, store
  original at `library/{sha256}.{ext}`, insert a `queued` row, run
  `ffmpeg -y -i <in> -ac 1 -ar 44100 <out>.wav` to `library/{sha}/source.wav`
  with stderr captured into a 500 on failure, then flip the row to `done`.
- Dedup returns the **existing** id with status **200** (no new row, no new
  files); a fresh upload returns **201**. Both share one Pydantic response
  model `MediaIdResponse { id: str }` (in `app/main.py`).
- `app/persistence.py` gained three small helpers next to the existing CRUD:
  `get_media_by_sha256`, `update_media_status` (returns the new row), and
  `source_wav_path(sha)` → `library/{sha}/source.wav` (sits beside
  `chords_path` → `library/{sha}/chords.json`, which T0005 will write).
- `app/main.py` adds `POST /media` (multipart field `file`). It maps
  `UploadError` to `HTTPException` so 413/415 bodies read
  `{"detail": ...}` like the rest of the API.
- Tests in `tests/test_uploads.py` synthesize a valid mono WAV with stdlib
  `wave` (no fixture file on disk) and exercise the happy path (201 + both
  files exist), byte-identical dedup (200, same id, single row), 413, and 415
  (both unknown-ext and disallowed-ext). Each test points `persistence` at a
  tmp library dir via monkeypatch so the repo's `library/` is never touched.
- Note on the persistence default-arg gotcha: `open_db(db_path=DB_PATH)` and
  friends bind their defaults at function-definition time, so monkeypatching
  `persistence.DB_PATH` later does **not** change calls that omit the arg.
  `ingest_upload` and the tests pass `persistence.DB_PATH` explicitly; future
  callers that want a non-default location should do the same. Not refactored
  (surgical scope); flagged here so the next task isn't surprised.
- Verified end-to-end against a live `fastapi dev` instance: 201 on upload,
  200 dedup, 413 over the limit, 415 for `.txt`/`.ogg`, and `source.wav`
  is a real RIFF WAVE mono 44100 Hz file produced by ffmpeg.
- Status codes: 201 new, 200 dedup, 413 too large, 415 unsupported format,
  500 if ffmpeg fails. Queueing is intentionally a no-op here per scope;
  T0005/T0006 replace the immediate `queued → done` flip with real jobs.
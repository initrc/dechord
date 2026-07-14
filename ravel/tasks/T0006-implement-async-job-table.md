---
id: T0006
title: Implement async job table and poll endpoint
status: done
dependencies:
  - T0002
  - T0005
---

# Scope

- Add a `job` table to `library/index.db`: `job(id, media_id, stage, status, progress, error, created_at, updated_at)`.
- Implement a job runner using FastAPI `BackgroundTasks` that runs the chord recognition service (T0005) and updates the job row through `queued → recognizing → done | failed`.
- Implement `GET /jobs/{id}` returning `{ status, progress, media_id }` per design-v1.md. `status` ∈ `queued | recognizing | done | failed`. `progress` is a coarse integer percent (or 0/100 for v1).

# Acceptance

- After `POST /media` (in T0003, wired here) queues a recognition job, `GET /jobs/{id}` transitions through `queued` → `recognizing` → `done`.
- After completion, `GET /media/{id}` returns `has_chords: true` and `chords: [...]` (the integration with T0007 lands there, but the row update made in T0005 must be visible).
- A failed recognition sets `status: failed` and populates `error`; `GET /jobs/{id}` returns the error message.
- Only one stage exists in v1 (`chords`); the `stage` column is reserved for future siblings (beats, key).
- Lint passes.

# Implementation Notes

- FastAPI `BackgroundTasks` runs tasks in the same process — adequate for single-user local use. A real queue (arq + Redis) is deferred (design-v1.md Backend).
- `progress` coarse is fine: 0 at queued, 50 at recognizing-start, 100 at done. Fine-grained per-frame progress would require hooking into madmom's processor; deferred.
- Job `id` is a short unique string with a `job_` prefix (mirroring the `media_` convention).
- Wire the actual queueing to `POST /media` here — T0003 created the row in `queued` but did not enqueue anything. Update T0003's endpoint to call the job runner.
- Reference: `ravel/docs/design-v1.md` Backend, Endpoint surface.

# Results

- `job` table added to `library/index.db` via a second `CREATE TABLE IF NOT
  EXISTS` (`JOB_SCHEMA_SQL`) run alongside `media` in `open_db`. Schema is
  exactly as scoped: `job(id, media_id, stage, status, progress, error,
  created_at, updated_at)` with a FK to `media(id)`. `stage` defaults to
  `chords` and is not otherwise exercised in v1.
- `app/persistence.py` gained `JobRow`, `new_job_id` (`job_` + 8 hex, mirroring
  `media_`), and `insert_job` / `get_job` / `update_job`. `update_job` takes an
  optional subset of `status` / `progress` / `error` and always bumps
  `updated_at`. `MediaStatus` is reused for job status — the lifecycle values
  (`queued | recognizing | done | failed`) are identical, so a separate enum
  would be duplicate code for no v1 benefit.
- `app/jobs.py` (new) owns `run_recognition_job`, the FastAPI `BackgroundTasks`
  function. It flips the job `queued → recognizing` (progress 50) and the media
  row to `recognizing`, delegates to `recognize_chords` (T0005, which sets the
  media row `done | failed` and writes `chords.json`), then flips the job to
  `done` (progress 100) or `failed` (capturing the exception message in
  `error`). The exception is not re-raised — the job row is the record;
  `logger.exception` keeps the traceback in the logs.
- `POST /media` now wires the queue: on a fresh upload it inserts a `queued`
  job and enqueues `run_recognition_job`. The placeholder `queued → done` flip
  in `ingest_upload` (T0003) is removed; the media row stays `queued` until the
  runner drives it. Dedup uploads still return the existing id with 200 and do
  not re-queue.
- `GET /jobs/{job_id}` returns `{ status, progress, media_id, error }`
  (404 if unknown). `error` is `null` unless `status == failed`; it's additive
  over design-v1.md's `{ status, progress, media_id }` so the frontend can
  surface the failure message, per the acceptance criterion.
- **Contract extension (flagged for review):** `POST /media` now returns
  `{ id, job_id }` instead of `{ id }`. design-v1.md specifies `POST /media →
  { id }` (the media id), but the acceptance here requires polling
  `GET /jobs/{id}` after `POST /media`, which needs the job id. The change is
  additive (`job_id` is omitted on dedup via `exclude_none=True`, so the dedup
  response is still `{ id }`); the frontend tasks (T0009, T0012) can poll
  either `GET /jobs/{job_id}` or `GET /media/{id}`. If the reviewer prefers a
  different shape (e.g. a `GET /media/{id}/job` lookup instead), this is the
  place to push back.
- Tests: `tests/test_jobs.py` (new, 6 tests) covers the runner's
  `queued → done` transition, the `recognizing` intermediate state (an
  observing fake reads the job/media rows mid-recognition), the `failed` path
  with error capture, the `GET /jobs/{id}` happy path + 404, and an
  end-to-end `POST /media` → `GET /jobs/{id}` is-done check.
  `tests/test_uploads.py` was updated: the `client` fixture now monkeypatches
  `recognition.get_recognizer` with a fake, because Starlette's `TestClient`
  runs `BackgroundTasks` to completion before returning — without the fake the
  upload tests would load madmom. The happy-path test additionally asserts
  `job_id` is returned and `has_chords` is true after the background task.
- All three gates pass: `uv run ruff check .` (clean), `uv run mypy app tests`
  (Success: no issues found in 10 source files), `uv run pytest` (18 passing).
---
id: T0006
title: Implement async job table and poll endpoint
status: new
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
---
id: T0003
title: Implement upload endpoint
status: new
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
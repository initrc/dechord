---
id: T0002
title: Define persistence schema and library storage
status: new
dependencies:
  - T0001
---

# Scope

- Define the SQLite schema (`library/index.db`) for the `media` table per the design doc: `media(id, sha256, original_filename, uploaded_at, duration, status, has_chords)`.
- Implement helpers to open the database, run idempotent migrations on startup (define on first task; no formal migration framework needed), and CRUD media rows.
- Implement the content-hash addressed file storage on disk under `library/` (flat layout — no sharding directory; see design-v1.md Media library).

# Acceptance

- On backend startup, `library/index.db` is created if missing with the `media` table; restarting the server does not error on an existing DB.
- A helper can insert a media row, fetch it by `id`, and list rows. Round-trip verified by a small script or test.
- A helper can write a media file to its content-hash-addressed path (`library/{sha256}.{ext}`) and read it back.
- Lint passes; the persistence module has type hints and no obvious SQL injection surface (use parameterized queries).

# Implementation Notes

- Use stdlib `sqlite3` directly — no ORM. The schema is tiny by design (design-v1.md Backend section).
- `id` is a short unique identifier; propose `media_` prefix plus a short random suffix (e.g., 8 chars from `secrets`). Keep it distinct from `sha256` (which is content-addressing for dedup, not a row identifier).
- Storage layout is flat: `library/{sha256}.{ext}` and `library/{sha256}/chords.json`. No two-char hash prefix directory (resolved in the design discussion).
- Define `status` enum in Python: `queued | recognizing | done | failed`. Match the strings used by `GET /jobs/{id}` (design-v1.md).
- Migrations are trivial: a single `CREATE TABLE IF NOT EXISTS` is sufficient for v1. Evolve the approach only when columns change.
- Reference: `ravel/docs/design-v1.md` Media library section.
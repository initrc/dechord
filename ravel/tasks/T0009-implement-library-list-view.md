---
id: T0009
title: Implement library list view
status: done
dependencies:
  - T0007
  - T0008
---

# Scope

- Implement the library list view (view 1 in design-v1.md): an upload box at the top, a table of media items below, and a per-row "Re-run recognition" button.
- Upload posts to `POST /media`; the table reads from `GET /media` and polls `GET /jobs/{id}` for any in-flight items until they reach `done`/`failed`.
- Clicking a row navigates to the item view (T0010/T0011).

# Acceptance

- Uploading a file via the upload box creates a row in the table with status `queued` and begins polling.
- The row's status transitions `queued → recognizing → done` (or `failed` with the error surfaced inline) without a full page reload.
- After completion, `has_chords` is visible as true.
- The "Re-run recognition" button calls `POST /media/{id}/chords`, receives a `job_id`, and the row re-polls until the new job completes.
- Clicking a row navigates to `/media/{id}` (route defined in T0010).
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- Use shadcn primitives (Table, Button, Input for the upload box) — the Lyra preset preinstalls them.
- Polling interval: 1–2 seconds. Stop polling when the job status is terminal.
- Upload progress (file upload bytes) is browser-native; the recognition progress shown is the `progress` field from `GET /jobs/{id}` (coarse 0/50/100 in v1).
- Route stub for `/media/{id}` should land in T0010; here, the row click can navigate to a placeholder route.
- Reference: `ravel/docs/design-v1.md` Frontend section, view 1.
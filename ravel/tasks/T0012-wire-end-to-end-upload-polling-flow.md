---
id: T0012
title: Wire end-to-end upload and polling flow
status: new
dependencies:
  - T0006
  - T0009
  - T0011
---

# Scope

- Close the loop: ensure the full user flow from upload (library list view, T0009) through job polling (T0006 backend poll endpoint) to item view (T0010 + T0011) works end to end without page reloads.
- Confirm the in-flight job state is visible in both the library list (per-row polling) and the item view (when navigated to before recognition completes).

# Acceptance

- Uploading a song from the library list transitions the row to `recognizing` and then `done` automatically via polling.
- Navigating from the library list to the item view while the job is still `recognizing` shows a placeholder (no chord track yet) and resolves to the rendered chord track + waveform once the job completes — verified by polling from the item view as well.
- Re-running recognition from the library list (`POST /media/{id}/chords`) re-flows through the same lifecycle: row returns to `recognizing`, the item view if open also reflects the in-flight state and resolves on completion.
- A failed job surfaces the error message in both views.
- `pnpm typecheck`, `pnpm lint`, and `ruff check .` all pass.

# Implementation Notes

- This task is mostly integration glue: ensuring both views poll `GET /jobs/{id}` and update on terminal status. The pieces exist from T0006, T0009, and T0010/T0011; this wires them together.
- Do not introduce a global state store (redux, zustand) unless shadcn Lyra preset already includes one — keep it minimal. Local component state plus polling is enough for v1.
- If the user navigates away during recognition, the media row's `status` in SQLite is the source of truth — reopening the item view reads from `GET /media/{id}`, not from a stale in-memory poll.
- Reference: `ravel/docs/design-v1.md` Backend and Frontend sections.
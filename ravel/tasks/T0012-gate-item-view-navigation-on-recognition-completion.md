---
id: T0012
title: Gate item view navigation on recognition completion
status: done
dependencies:
  - T0006
  - T0009
  - T0011
---

# Scope

- Close the loop: ensure the full user flow from upload (library list view, T0009) through job polling (T0006 backend poll endpoint) to item view (T0010 + T0011) works end to end without page reloads.

# Acceptance

- Uploading a song from the library list transitions the row to `recognizing` and then `done` automatically via polling.
- Navigating to the item view is only allowed when `status === "done"`. Rows with `queued`, `recognizing`, or `failed` status are dimmed and not clickable — there is no value in landing on a page with no chords to display.
- Re-running recognition from the library list (`POST /media/{id}/chords`) re-flows through the same lifecycle: row returns to `recognizing`, becomes unclickable, and resolves to clickable `done` on completion.
- A failed job surfaces the error message in the library row via the existing polling.
- `pnpm typecheck`, `pnpm lint`, and `ruff check .` all pass.

# What was done

Simplified from the original plan: instead of adding client-side polling to the item view page (which would show a spinner with no useful content), navigation is simply gated on `status === "done"`. This eliminates the need for a `MediaDetailView` wrapper, `job_id` query params, and duplicate polling in the item view. The item view page remains a server component.

**Changes:**
- `frontend/components/library-view.tsx`: rows are only clickable when `displayStatus === "done"`; non-terminal rows are dimmed (`opacity-70`, `cursor-default`).
- `frontend/app/media/[id]/page.tsx`: reverted to original server component (no polling, no `searchParams`).
- `frontend/components/item-view.tsx`: reverted (no `status`/`error` props).

**Not done (intentionally):**
- No polling or in-flight UI in the item view — you can't reach it before recognition completes.
- No re-run button in the item view — library view re-run is sufficient for v1.
- No global state store — existing local component state + polling is enough.

# Implementation Notes

- The pieces from T0006 (poll endpoint), T0009 (library list with per-row polling), and T0010/T0011 (item view) were already wired; this task added the navigation gate.
- The media row's `status` in SQLite is the source of truth — the library list refreshes on job completion and the row becomes clickable.
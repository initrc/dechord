---
id: T0014
title: Make PX_PER_SECOND responsive
status: new
dependencies: []
---

# Scope

- Change `PX_PER_SECOND` from the hardcoded `22` to a responsive value: `22` on mobile and `32` at `sm:` and above, matching the existing `sm:` breakpoint where `22` already looks good per the user's report.

# Acceptance

- At viewport widths below `sm`, layout uses 22 px/sec; at `sm` and above, layout uses 32 px/sec.
- The chord squares, master waveform canvas widths, and seek-on-click math (`x / PX_PER_SECOND` in `frontend/components/item-view.tsx:87`) all use the same responsive value at the same breakpoint — no misalignment between chord track and master track after a viewport change.
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- `PX_PER_SECOND` is currently a `const` exported from `frontend/lib/timeline.ts:1` and imported by `frontend/components/master-track.tsx:5` (canvas width math, `secondsPerPx = 1 / PX_PER_SECOND` at `frontend/components/master-track.tsx:46`) and `frontend/components/item-view.tsx:9` (seek math, `secondsToPx` for row widths). A bare `const` won't track viewport changes.
- Mirror the `useRowSeconds` pattern already in `frontend/lib/layout.ts:38` (reads a CSS variable off a container via `getComputedStyle`, re-reads on `resize`). Add a CSS variable e.g. `--px-per-second:22 sm:[--px-per-second:32]` to the same container in `frontend/components/item-view.tsx:48` (next to the existing `[--row-seconds:15] sm:[--row-seconds:30]`), and add a `usePxPerSecond` hook. Replace the `PX_PER_SECOND` import with the hook return value everywhere it is read at render time.
- `secondsToPx` / `formatTime` in `frontend/lib/timeline.ts` are pure functions; they need a `pxPerSecond` argument now (or replace callsites with inline multiplication). Don't leave a stale `PX_PER_SECOND` const — if no one reads it after the change, remove it.
- Note: `useRowSeconds` reads the CSS var on mount *and* on `resize`. Manually toggling the devtools viewport width without firing `resize` is not in scope.
- Watch the canvas in `master-track.tsx`: its `width` is read inside `useEffect` deps already, so the redraw will re-run when the hook's value changes — verify the canvas actually re renders at the new width on `sm:` ⇄ `base` transitions.
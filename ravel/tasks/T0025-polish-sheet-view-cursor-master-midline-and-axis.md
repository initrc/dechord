id: T0025
title: Polish sheet view cursor, master midline, and axis
status: review
dependencies: []
---

# Scope

- Make the sheet view playhead cursor fully visible as a 2px-wide vertical line (already done in `sheet-view.tsx`).
- Add a hairline running horizontally through the middle of each `MasterTrackRow`.
- Strip the `TimelineAxis` down to a single tick at the start of each row, and anchor that tick's bottom to the bottom of the `MasterTrackRow` (i.e. the axis no longer sits in its own strip below the row).
- Drop the now-unused tick list from `TimeRow` and the `tickInterval` helper.
- Rename `timeline-axis.tsx` / `TimelineAxis` to `row-start-label.tsx` / `RowStartLabel`.
- Fix 1-2px of track content overflowing the right border on the last row (pre-existing bug).

# Acceptance

- The playhead is a continuous 2px line spanning the full height of every row where it is active, never clipped.
- Each `MasterTrackRow` shows a centered horizontal hairline across its full width.
- `RowStartLabel` renders exactly one label per row (at `row.rowStart`), positioned with its bottom against the `MasterTrackRow`'s bottom edge; no separate axis strip remains below the row.
- `TimeRow` no longer carries a `ticks` array; `tickInterval` is removed.
- The last (short) row's canvas and chord track do not bleed past the bordered box's right edge.
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- Cursor (#1) was already implemented in `frontend/components/sheet-view.tsx` via an absolutely-positioned 2px `bg-primary` div.
- Midline (#2): added an absolutely-positioned 1px `bg-primary/10` div inside the `MasterTrackRow` wrapper, centered with `top-1/2 -translate-y-1/2`. Matches the row border tint.
- Axis (#3): rewrote the former `timeline-axis.tsx` to render a single `formatTime(row.rowStart)` span anchored `absolute bottom-0 left-0`. Removed `AXIS_HEIGHT`, the `width`/`pxPerSecond` props, and the `secondsToPx` import. In `frontend/components/sheet-view.tsx`, moved the label inside the bordered row box.
- Cleanup (#4): removed the `ticks` field from `TimeRow` in `frontend/lib/layout.ts`, dropped the tick-building loop in `buildTimeRows`, and deleted the now-unused `tickInterval` from `frontend/lib/timeline.ts`.
- Rename (#5): renamed `timeline-axis.tsx` → `frontend/components/row-start-label.tsx` and the component `TimelineAxis` → `RowStartLabel`, since it is now a single per-row label rather than an axis. Tightened spacing to `px-0.5 text-[8px]` so the label fits within the track row.
- Overflow fix (#6): the row bordered box used Tailwind's `box-sizing: border-box` but its `width`-sized children (canvas, chord track) didn't account for the 2px of border, so they overflowed by up to 2px on the right. Root cause turned out to be subpixel rounding, not just border math; several follow-ups were needed:
  - `frontend/lib/timeline.ts`: `secondsToPx` now `Math.round`s, so row/canvas/cursor widths all snap to the same device pixel.
  - `frontend/components/chord-track.tsx`: tile segments by accumulation; the last segment fills `width - consumed` so the chord track's right edge aligns exactly (independent rounding left a 1px gap on rows with many segments).
  - `frontend/components/sheet-view.tsx`: merged the two nested divs into one `border border-primary/10` element sized `width + 2` (border-box → content = `width`). Cursor offset shifted from `secondsToPx(...) - 1` to `secondsToPx(...)` so the full 2px is visible at t=0 against the left border. `items-center` removed (no slack to center; at zoom it caused a left-edge gap).
  - Tried `outline` instead — works but extends outside the box, and the `overflow-x-hidden` parent flips to `overflow-y: auto`, producing a vertical scrollbar. Reverted to `border`.
- Related seam/border work was done in T0015 and T0021.
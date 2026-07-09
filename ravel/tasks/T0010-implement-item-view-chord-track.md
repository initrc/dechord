---
id: T0010
title: Implement item view chord track
status: new
dependencies:
  - T0007
  - T0008
---

# Scope

- Implement the `/media/{id}` route and the chord track (the top row of the item view in design-v1.md).
- Render the chord rows from `chords[]` from `GET /media/{id}`: a horizontal row of labeled rectangles, widths proportional to `end - start`, labels parsed with `tonal.js` for display (root, quality).
- The `<->` axis is `mm:ss` seconds. No bar ruler (per design-v1.md Out of scope).
- Make the track scrollable if the song is long, with a stable total-width layout.

# Acceptance

- Given a media item with `chords` populated, the route renders the chord track with one rectangle per chord, widths matching `end - start`, labels readable.
- The mm:ss axis ticks appear at regular intervals; the track aligns with the master track rendered in T0011.
- Empty or `N` (no-chord) segments render as a blank rectangle (no label) rather than as text "N".
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- This task delivers the static (non-playing) chord track. The playback cursor that sweeps in sync with the master transport lands in T0011.
- Use `tonal.js` `Chord` to parse the `root:quality` labels — though v1 vocabulary is just maj/min/N, parse robustly enough to display more if the recognizer is later upgraded.
- Layout shapes (rectangle width per second) must match between chord track and master track — share a `secondsToPx` helper between the two tracks. T0011 will reuse it; define it here in a small shared module.
- Capture a fixed visible-time-window scroll approach if needed; do not over-engineer. A simple scroll container with a wide inner div is fine for v1.
- Reference: `ravel/docs/design-v1.md` Frontend section, view 2.
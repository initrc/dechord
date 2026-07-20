---
id: T0010
title: Implement item view chord track
status: done
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

## Decisions made during implementation

- **No CORS middleware**: The backend no longer sets CORS headers. The frontend proxies API calls through Next.js rewrites (`/api/:path*` → backend), so both share the same origin.
- **`original_filename` in `GET /media/{id}`**: Added to the response so the item view can display the filename (without extension) as the page title instead of the media hash.
- **Simplified chord notation**: Labels display as `C`, `Am`, `F#m` etc. (major = root only, minor = root + `m`) rather than `C major` / `A minor`.
- **Multi-row sheet music layout**: Chords are laid out in multiple horizontal rows instead of a single scrollable row. `ROW_SECONDS` is configurable (15s on mobile, 30s on desktop via Tailwind responsive CSS variable `[--row-seconds:15] sm:[--row-seconds:30]`).
- **Chord splitting across rows**: Chords that cross row boundaries are split. Part 1 shows the label, Part 2 is blank. Both parts share the same background color to indicate they are the same chord.
- **Three segment colors**: Two alternating colors for chord backgrounds (`bg-primary/10`, `bg-primary/5`) and one for silence (`bg-muted/10`). Split chord parts inherit the color of their parent chord.
- **Duration display**: Uses `Math.ceil` instead of `Math.round` to avoid rounding down (e.g., 98.7s shows as 99s, not 98s).
- **Server-side fetch URL**: The API client uses relative URLs on the client and constructs absolute URLs (`http://localhost:3000/api/...`) on the server for SSR.
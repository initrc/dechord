---
id: T0011
title: Implement item view master track and transport
status: new
dependencies:
  - T0010
---

# Scope

- Implement the master track (bottom row of the item view): a thin waveform of the source upload fetched via `GET /media/{id}/audio/source`.
- Implement the shared transport: play/pause/seek controls that drive Web Audio playback of the master track and sweep a cursor across both tracks in sync (chord track from T0010 + master track here).

# Acceptance

- The item view renders two stacked tracks with a single horizontal timeline: chord track on top, master waveform below, both aligned to the same `mm:ss` axis.
- Play and pause control the master audio via Web Audio; the playback cursor moves across both tracks in sync.
- Seeking (click on the timeline) repositions the cursor and seeks the audio to that time.
- During playback, the cursor tracks audio time from the Web Audio clock (not a JS timer) — no drift on the chord track cursor.
- When audio ends or is paused, the cursor stops and remains at its position.
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- Use the Web Audio API. Load the source audio via `fetch` + `decodeAudioData`. Use `AudioContext.currentTime` as the clock source for the cursor to avoid JS-timer drift.
- Waveform drawing: a simple peak-per-pixel or RMS-per-pixel drawn to a `<canvas>` is sufficient. Don't pull in `wavesurfer.js` or similar unless already in the preset — the design doc only calls for a thin waveform.
- Playback of the master track only — no mute/solo, no per-stem playback (Out of scope, design-v1.md).
- The transport is one shared widget; both tracks use the same `secondsToPx` helper introduced in T0010.
- Loading the audio each navigation is fine for v1 — caching is premature.
- Reference: `ravel/docs/design-v1.md` Frontend section, view 2.
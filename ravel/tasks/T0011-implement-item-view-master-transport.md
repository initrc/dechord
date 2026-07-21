---
id: T0011
title: Implement item view master track and transport
status: done
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

## Decisions made during implementation

- **Per-row stacked layout (shared axis per row)**: Each row renders the chord strip, master waveform, and axis together, so the "two stacked tracks share one horizontal timeline" semantics holds per multi-row chunk. The previous single `ChordTrack` block was split into a per-row `ChordTrackRow` so the master track can interleave with it.
- **Shared row layout extracted to `lib/layout.ts`**: `useRowSeconds` (CSS-var-driven responsive `--row-seconds:15 sm:30`) and `buildTimeRows` live there. `ChordTrack` and `MasterTrack` both call `buildTimeRows` so chord squares and waveform columns align at the same `mm:ss` boundaries.
- **Waveform**: thin peak-per-pixel canvas (max abs amplitude over the sample range covered by that pixel column), one canvas per row. Theme-aware color sourced from `--muted-foreground` so it follows light/dark without a hardcoded hex.
- **Audio clock from `AudioContext.currentTime`**: `useAudioPlayer` records `startCtxTime`/`startOffset` at `node.start()`, and a `requestAnimationFrame` loop reads `startOffset + (ctx.currentTime - startCtxTime)` to drive `currentTime`. No JS-interval drift.
- **Audio preloaded on mount**: `decodeAudioData` runs on a suspended AudioContext on first mount so the waveform renders before the user hits play; `resume()` still waits for the play-button gesture inside `play()`.
- **Cursor is one DOM overlay per row**: when `currentTime` falls within a row's `[rowStart, rowEnd)`, a 2px `bg-primary` line spans both the chord strip and the master strip — visually one continuous playhead across the two tracks. Only the row containing `currentTime` shows the cursor.
- **Seek on click anywhere on the row block**: clicking the chord strip, master strip, or axis computes `rowStart + x / PX_PER_SECOND` and calls `player.seek`, which restarts the AudioBufferSourceNode from the new offset if currently playing.
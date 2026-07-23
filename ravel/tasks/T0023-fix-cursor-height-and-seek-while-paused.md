---
id: T0023
title: Fix cursor height and seek-while-paused
status: review
dependencies: []
---

# Scope

Two bugs in the item view, both guarded by `cursorActive` in `frontend/components/item-view.tsx`:

1. After the chord/master tracks were wrapped in a bordered div, the playback cursor (a 2px-wide absolutely-positioned bar) was sized with a hardcoded `height: trackBlockHeight` that ignored the border, leaving a ~2px gap at the bottom.
2. After the rAF-based playback loop was introduced in `frontend/lib/audio-player.ts`, seeking while paused stopped moving the cursor. `seek` mutates `audio.currentTime` but never updates React state, and the rAF `currentTime` sync loop only runs while `isPlaying` is true, so the cursor stays frozen until playback resumes.

# Acceptance

- The cursor fills the full height of the bordered tracks container (no visible gap) for all row widths and theme color settings.
- Clicking anywhere on the tracks moves the cursor immediately, whether the player is playing or paused.
- The project builds, passes lint, and passes typecheck (`npm run typecheck && npm run lint`).

# Implementation Notes

- `frontend/components/item-view.tsx`: moved the cursor inside the `border` wrapper (the `<div className="border border-primary/10">` at line 88, now `relative`) and replaced `height: trackBlockHeight` with `inset-y-0` so it always matches the bordered container. Removed the now-unused `trackBlockHeight` and its `CHORD_HEIGHT`/`MASTER_HEIGHT` imports.
- `frontend/lib/audio-player.ts`: in `seek`, added `setCurrentTime(audio.currentTime)` after assigning the audio element's time so the React state stays in sync without the rAF loop.
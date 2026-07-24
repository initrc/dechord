---
id: T0026
title: Fix long-track playback pause from network underrun
status: review
dependencies:
  - T0016
---

# Scope

- Fix the regression T0016 introduced: long tracks (5+ min) pause mid-playback (around ~4:30, timing varies with download throughput) and `currentTime` freezes. Resolves the streaming-buffer underrun that T0016's `new Audio(streamingUrl)` + `preload="auto"` swap created when it replaced the in-memory `decodeAudioData` buffer.

# Acceptance

- A 5-minute track plays to its natural end without a mid-playback freeze, even when the link between the browser and `/api/media/{id}/audio/source` is throttled below the audio's bitrate.
- No `waiting`/`stalled` events fire during straight-through playback of a buffered-ahead blob.
- Waveform (peaks) still renders from the separate `/audio/peaks` endpoint, unaffected by the playback fix.
- `pnpm typecheck` and `pnpm lint` pass.
- Cleanup is safe on React Strict Mode double-mount and on `mediaId`/`duration` change: in-flight fetch aborts, audio pauses, blob URL revokes, ref clears.

# Implementation Notes

## Root cause

- T0016 (`frontend/lib/audio-player.ts:23`, commit `41e6b02`) replaced the Web Audio `AudioBuffer` (whole file decoded up front via `decodeAudioData`, resident in memory) with `new Audio(url)` + `preload="auto"`. The latter is a streaming player: Chrome pulls byte ranges lazily and fetches more only as the buffered-ahead gap closes.
- If throughput can't keep pace with realtime (slow link, or Chrome's adaptive fetch settling into a low rate), the buffered-ahead region underruns partway through a long track. The element fires `waiting` + `stalled` and `currentTime` freezes until more bytes arrive — which under a slow link can be never within the playback session.
- Reproduced under Chrome CDP `Network.emulateNetworkConditions` at 30 KB/s: a 5:06 track stalls at ~4:53 with `currentTime` frozen at 292.851 and `bufferedEnd` 292.92, never resuming. Before T0016 the file was resident in memory, so this underrun was physically impossible — the regression.
- The exact stall time depends on download rate vs. playback rate, which matches the user's "around 4:30, not consistent" report.

## Fix

- `frontend/lib/audio-player.ts:32` — fetch the entire source once into a `Blob` on mount, then assign the resulting `blob:` URL to the `HTMLAudioElement` (instead of pointing it at the streaming URL). Once assigned, the element reads from in-memory bytes, so an underrun during playback is impossible — the same guarantee the old `decodeAudioData` path had.
- Keeps T0016's small HTMLAudio code shape: no `AudioContext`, no `AudioBufferSourceNode`, no `startCtxTime`/`startOffset` bookkeeping, no rAF clock.
- Peaks/waveform load from `/api/media/{mediaId}/audio/peaks` (T0017) and render immediately, unaffected. Only the play button waits on the blob fetch (≈ a few hundred ms on localhost; the button is already disabled while `loading`).
- Cleanup: `AbortController` aborts the in-flight fetch; `audio.pause()` + removeEventListener; `URL.revokeObjectURL(url)`; `audioRef.current = null`. Handler list dropped `canplay` (no longer needed — `loading` flips to false once the blob-backed element is constructed and wired).

## Caching behavior

- The Blob lives in React state for the component's lifetime; a page refresh discards it and the effect re-fetches. There is no explicit cross-session blob cache.
- The backend's `FileResponse` (`backend/app/main.py:189`) sends `ETag` + `Last-Modified` + `accept-ranges: bytes`, so the refresh fetch is served from the browser HTTP cache — typically a 304 (revalidation, no body) or a disk-cache hit if recent. The audio file body is not re-transferred across the wire; only the JS-side Blob is rebuilt each mount.

## Verification

- Same throttled repro after the fix: `bufferedEnd` is full `305.92` from the moment playback starts; `currentTime` advances continuously to `305.920` and ends naturally with `pause` + `ended`. No `waiting`/`stalled`.
- Unthrottled repro: clean end-to-end completion as well.

## References

- `frontend/lib/audio-player.ts:32` — the blob-fetch-and-assign effect this task adds.
- T0016 — the swap that introduced the regression (commit `41e6b02`).
- T0017 — server-precomputed peaks endpoint, which is what lets us re-introduce an upfront full download without re-blocking the waveform render.
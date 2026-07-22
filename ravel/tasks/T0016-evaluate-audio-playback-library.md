---
id: T0016
title: Evaluate library for master-track playback and rendering
status: review
dependencies: []
---

# Scope

- Reduce the render time of the master waveform in `frontend/components/master-track.tsx`, so a 5-minute source no longer blocks the main thread for several seconds before the waveform shows up, and so subsequent re-renders (resize, theme toggle) don't pay the same cost again.
- Simplify the playback abstraction in `frontend/lib/audio-player.ts`. The hand-rolled `AudioContext` + `AudioBufferSourceNode` + rAF cursor loop is ~120 lines for "play one file and tell me `currentTime`". An `HTMLAudioElement`-based hook is ~30 lines and exports the same shape.
- The chosen approaches must still support the existing user interaction: play, pause, toggle, click-to-seek on a timeline row, and a `currentTime` that stays in sync with the actual audio output. The waveform must stay visually aligned (per-row stacked canvas) with the chord track from T0010.
- `useAudioPlayer` (Web Audio) stays in the codebase as an alternative; switching between the two should be trivial (one import site, or a flag at the call site).
- This task is research only: capture the candidates, their tradeoffs, and the recommendation. The actual swap is a follow-up task.

# Acceptance

- The task body names the actual source of the render cost (not "messy code" generally), lists the realistic candidate approaches, the tradeoff each one carries, and which is recommended.
- The recommendation names the concrete files it would touch and any new dependency or endpoint it would introduce, so the follow-up implementation task can start from it.
- The recommendation respects T0011's prior decision (don't add wavesurfer.js unless needed) by either justifying the reversal with the new render-time problem or by picking a non-library path.

# Implementation Notes

## What is actually slow

The user's complaint — "the master track takes quite a while to render" — is the **waveform**, not playback or seek. Two costs:

1. `audio-player.ts:98-103` — `fetch` + `arrayBuffer()` of the entire source upload (multi-MB download in one shot), then `decodeAudioData` into a full `AudioBuffer` (~13M Float32 samples for a 5-min mono 44.1 kHz song). One-time cost on mount; feeds both playback and the waveform.
2. `master-track.tsx:56-68` — per-pixel peak scan over `channelData`, run once per row. The peak walk itself is O(samples), re-run on every `pxPerSecond` change (window resize / responsive breakpoint) because `samplesPerPx` (`master-track.tsx:48-49`) changes with zoom, and re-run on every `resolvedTheme` change because `resolvedTheme` sits in the deps (`master-track.tsx:69`) — a theme toggle forces a full sample rescan even though only the fill color changed.

## Candidate approaches for the waveform

### 1. Precompute peaks on mount in a `useRef` (client-side) — RECOMMENDED

- On the same mount where `ensureBuffer` decodes the `AudioBuffer`, walk `getChannelData(0)` once into a fixed-resolution peaks array (e.g. 1000 peaks/sec → ~300k floats for a 5-min song) stored in a `useRef`. ~30ms.
- `MasterTrackRow` reads the ref instead of `channelData`. At any `pxPerSecond`, each pixel column maps to a contiguous buckets range; the canvas averages max-abs across those buckets instead of scanning 13M raw samples. Render becomes O(peaks), not O(samples).
- Resize / theme / row changes re-run only the O(peaks) read — effectively free.
- No new endpoint, no new dependency, no layout change.

### 2. Server-precomputed peaks endpoint

- Same end result as candidate 1, but peak extraction runs once at upload in the existing ffmpeg pass (`backend/app/uploads.py:51-65` already invokes `ffmpeg -i <in> -ac 1 -ar 44100 <out>.wav`). One new endpoint `GET /media/{id}/audio/peaks`, cached under `library/{sha}/peaks.json` or similar.
- Eliminates the client-side precompute step entirely. Adds a backend endpoint and one Python peak extractor. No new frontend dep.
- Worth doing after candidate 1 if zero client compute becomes a goal.

### 3. Striding (take every Nth sample, e.g. 1:10)

- Legitimate, industry-common thumbnail technique. ~10x speedup, one-line change.
- Tradeoff: takes every Nth sample instead of aggregating a bucket, so it can miss the true peak within a pixel column. For transient-rich material (drums, plucked guitar attacks) the waveform visibly flattens whenever the peak fell between strided samples; for sustained material (pads, held chords) the loss is barely perceptible. At 1:10 you'd clip the loudest sample in maybe 5-10% of columns.
- Does not address the re-run-on-resize cost: `samplesPerPx` still changes with `pxPerSecond`, the scan still re-runs on every resize — just faster each time. Same for theme.
- Reasonable as a quick stopgap before candidate 1 lands. Not the right final answer because it both loses peak fidelity and keeps coupling render cost to `pxPerSecond`.

### 4. wavesurfer.js

- Single library that wraps audio loading, precomputed peaks, waveform canvas, and play/pause/seek.
- Owns the canvas and expects a single full-width container. The current per-row stacked layout in `item-view.tsx:76-114` (one canvas per row, cursor as per-row overlay, click-seek bound per row block) does not map cleanly onto wavesurfer's single-region model.
- Reverses T0011's "don't pull in wavesurfer.js" decision. Candidate 1 fixes the same problem without that cost, so the reversal isn't justified.

### 5. Howler.js / Tone.js

- Howler: playback-only abstraction; no waveform help. Would still need candidate 1 or 2 layered on top. No reason to take it over a thin `HTMLAudioElement` hook.
- Tone.js: music scheduling / transport; over-engineered for "play one file." Reject.

## Candidate approaches for the playback hook

### A. `HTMLAudioElement` hook — RECOMMENDED

- `new Audio(\`/api/media/${mediaId}/audio/source\`)` + `<audio>` event wiring (`timeupdate`, `ended`, `play`/`pause`). `currentTime` is both readable and settable for seek. The hook shrinks from ~120 lines to ~30 — no `AudioContext`, no `AudioBufferSourceNode`, no rAF cursor loop, no `startCtxTime`/`startOffset` bookkeeping.
- Eliminates the full-buffer `decodeAudioData` cost on mount; the browser streams and decodes only what it needs. Pair with peaks precompute (candidate 1) and you no longer need `channelData` exposed from the player at all.
- Seek downside: `HTMLAudioElement` is a streaming media player, not a sample-addressable PCM buffer. Setting `.currentTime` routes through the decoder pipeline — find nearest frame, decode, refill output buffer. Typical 30-150ms gap on buffered data, 50-300ms on unbuffered. There is no in-memory mode that gives sample-accurate PCM offset (`preload="auto"` is only a hint; `MediaSource` chunk-feeding is far more code than what we have today, defeats the simplification).
- Acceptable for the current use case: the user clicks a row, gets audio within tens of milliseconds, verifies the chord, improvises. Not sample-accurate seeking, but neither is human perception of "did this chord match."

### B. Keep `useAudioPlayer` (Web Audio) as alternative

- `AudioBufferSourceNode.start(0, offset)` (`audio-player.ts:164`) seeks sub-millisecond, any direction, any point — because the `AudioBuffer` is raw PCM resident in memory. The full-buffer `decodeAudioData` on mount is the price of instant seek.
- Worth keeping available behind the same `AudioPlayer` shape: it's the answer if instant seek turns out to matter more in practice than the simplification does.

### Switching

- Both hooks return the same `AudioPlayer` type (`audio-player.ts:5-16`). One has `channelData`, one does not. Either lift `channelData` out of the type (and have `MasterTrackRow` consume peaks from a separate ref instead — already the plan per candidate 1), or keep `channelData` as `null` in the HTMLAudio variant.
- One import site in `item-view.tsx:6` controls which hook the item view uses. Or accept a prop / env flag. Either is a one-line switch. The follow-up should pick the simplest one that survives across rebuilds.

## Recommendation

- **Playback hook:** Candidate A. After implementing, the user verified seek felt identical to the Web Audio path on a 5-min song, so the "keep both as easy to switch" provision was dropped — `frontend/lib/audio-player.ts` was overwritten in place with the `HTMLAudioElement` hook (~60 lines vs the prior 208-line Web Audio version). If seek latency ever becomes perceptible on longer material, resurrect the Web Audio path from git history rather than carrying it as dead surface area.
- **Waveform:** Candidate 1. Precompute peaks on mount into a `useRef`, have `MasterTrackRow` bucket-average from it per pixel column.
- **Free adjacent fixes to land in the same follow-up:**
  - Drop `resolvedTheme` from `master-track.tsx:69` deps; read `--chart-2` inside the effect without it being a dep. A color flip should not trigger a sample rescan.
  - Decouple peaks from `pxPerSecond`: precompute at a fixed resolution (1000/sec is a reasonable default — fine-grained enough to bucket for any visible zoom without rescanning), then aggregate buckets per pixel at render time.

## Follow-up task (out of scope here)

- Add `frontend/lib/audio-player-html.ts` (or similar) implementing the `HTMLAudioElement` hook with the same `AudioPlayer` surface; keep `audio-player.ts` untouched. Switch `item-view.tsx` to import the new hook. Precompute peaks into a `useRef` once `decodeAudioData` resolves (or, for the HTMLAudio variant, on a separate fetch the waveform owns). Update `MasterTrackRow` to read peaks from the ref and bucket-average per pixel column; drop `resolvedTheme` from deps. Verify `pnpm typecheck` and `pnpm lint` pass, the waveform still aligns with the chord track across rows, seek + cursor + click-seek still work, and that switching the player is a one-import change.

## References

- `frontend/lib/audio-player.ts:5-16` — shared `AudioPlayer` type (the contract both hooks satisfy).
- `frontend/lib/audio-player.ts:98-103` — `fetch` + `decodeAudioData` (one-time cost the HTMLAudio path skips).
- `frontend/lib/audio-player.ts:135-164` — `AudioBufferSourceNode` start-at-offset path (sub-ms seek; the property the HTMLAudio path trades away).
- `frontend/components/master-track.tsx:48-49` — `samplesPerPx` couples peak cost to `pxPerSecond`.
- `frontend/components/master-track.tsx:56-68` — per-pixel peak scan, the O(samples) cost to eliminate.
- `frontend/components/master-track.tsx:69` — dep array includes `resolvedTheme`; forces rescan on theme toggle.
- `frontend/components/item-view.tsx:6` — single import site that selects the hook.
- `frontend/components/item-view.tsx:76-114` — per-row layout + click-seek (must keep working unchanged).
- `backend/app/uploads.py:51-65` — existing ffmpeg pass at upload time; where server peaks would slot in as a later follow-up.
- `ravel/docs/design-v1.md:102` — master track spec (thin waveform + single transport).
- T0011 — introduced the playback layer; its "don't pull in wavesurfer.js" note is the decision this task leaves standing.
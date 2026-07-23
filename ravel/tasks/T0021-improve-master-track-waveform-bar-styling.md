---
id: T0021
title: Improve master track waveform bar styling
status: done
dependencies: []
---

# Scope

- Make waveform bars 2px wide with 1px gaps and rounded corners.
- Draw bars with amplitude-based opacity (louder = more opaque) using `globalAlpha`.
- Add a container div wrapping the chord track and master track with a full border.
- Simplify chord segment borders to bottom-only for separation from the master track.
- Prevent horizontal scrollbar overflow from the new container.

# Acceptance

- Project builds, passes TypeScript type-checking, and passes lint.
- Waveform bars render as 2px wide rounded rectangles with 1px gaps on all sides (including row edges).
- Bar opacity scales with amplitude: minimum `0.3`, maximum `1.0` (`0.3 + peak * 0.7`).
- Chord and master tracks share a single bordered container; no horizontal scrollbar appears.

# Implementation Notes

- `frontend/components/master-track.tsx`: bar drawing uses `ctx.roundRect` with `globalAlpha` driven by peak amplitude. Gaps at row edges via `x = i * stepWidth + gapWidth` and `numBars = floor((width - gapWidth) / stepWidth)`.
- `frontend/components/sheet-view.tsx`: new `<div className="border border-primary/10">` wraps chord + master tracks only; parent flex column has `overflow-x-hidden`.
- `frontend/components/chord-track.tsx`: segment `borderClass` simplified to `"border-b"` — outer frame handled by container div.

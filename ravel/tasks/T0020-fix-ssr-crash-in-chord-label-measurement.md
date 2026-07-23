---
id: T0020
title: Fix SSR crash in chord label measurement
status: done
dependencies: []
---

# Scope

- The media page server-renders `ItemView` with chord data, so `buildChordRows` runs during SSR. Its label-fit check measured text via `document.createElement("canvas")`, crashing every server render with `ReferenceError: document is not defined` — the page returned `__next_error__` HTML and only recovered on the client.
- Replace DOM text measurement with a deterministic per-character width estimate that runs identically on server and client.

# Acceptance

- Media pages server-render without error: no `__next_error__` in the SSR HTML, no "document is not defined" in the dev overlay.
- Chord label placement is unchanged in practice: the estimate is biased slightly above measured widths, so a label that "fits" really fits; borderline labels move to the chord's wider split part instead of clipping.
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- `frontend/components/chord-track.tsx`: removed `createLabelWidthMeasurer`; `labelFits` now calls `estimateLabelWidth`.
- The old "lazily created on first call" guard only deferred the DOM access to the first measurement, which still happens inside the render — on the server.
- Why an estimate rather than client-only exact measurement: `showLabel` must be identical on server and client or React hydration mismatches, and exact text width requires a DOM. The alternative (defer exact measurement to a post-mount effect) adds state plumbing for no visible gain.
- Estimate calibrated against real 12px Inter widths ("Dm"=19.2, "A#"=15.9, "Cmin7"=36.1). Per-character classes: uppercase 9, m/w 10.5, i/j/l 3, everything else 7.5 — stays within ~3px above canvas truth for the chord-label vocabulary.

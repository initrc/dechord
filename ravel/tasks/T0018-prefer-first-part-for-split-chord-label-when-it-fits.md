---
id: T0018
title: Prefer first part for split chord label when it fits
status: done
dependencies: []
---

# Scope

- Change split-chord label placement so the first visible part of a cross-row chord carries the label whenever it is wide enough to fit the rendered label text. Only when the first part is too narrow should the label fall back to the wider of the two parts (the current T0013 rule).
- Chords fully contained in one row are unaffected.

# Acceptance

- Given a cross-row chord whose first part is wide enough to fit the label text (label width + padding <= first segment's pixel width), the label renders on that first part and the second part is blank.
- Given a cross-row chord whose first part is too narrow to fit the label, the label renders on whichever part is wider (T0013 behavior as fallback). If both parts are too narrow, still render on the wider part (no new hiding rule).
- Chords fully contained in one row still show the label on their single part.
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- The two-pass decision lives in `buildChordRows` in `frontend/components/chord-track.tsx:79`. Today Pass 2 picks the widest segment unconditionally; change it to first test the earliest segment by pixel width and only fall back to the widest when the earliest one cannot fit the label.
- "Fits the label text" means: text width of `seg.label` plus horizontal padding fits inside the segment's width in pixels. The segment width is derived via `secondsToPx(seg.end - seg.start, pxPerSecond)` (see `frontend/components/chord-track.tsx:107`); the rendered label uses `px-1` padding (~8px each side) per `frontend/components/chord-track.tsx:116`.
- Text width measurement must run on the client. Use a one-off canvas `measureText` (or a cached hidden span) rather than a layout read inside the render loop, to avoid layout thrash. Cache by `label` string since chord labels come from a small vocabulary.
- `pxPerSecond` is not available inside `buildChordRows` today (it is passed to `ChordTrackRow` separately at `frontend/components/chord-track.tsx:99`). Thread `pxPerSecond` into `buildChordRows` as a new parameter and update its caller.
- Silence segments (`isSilence`) keep their current behavior — never show a label, regardless of width.
- Color-index inheritance (`chordColorIndices` at `frontend/components/chord-track.tsx:29`) is unchanged; both split parts still share the parent chord's color.
- Supersedes the T0013 "always wider" rule for the first-fit case. T0013's fallback is retained for the narrow-first-part case. Depends on T0013 having landed (T0013 is done).
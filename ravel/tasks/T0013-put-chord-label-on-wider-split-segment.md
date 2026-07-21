---
id: T0013
title: Put chord label on wider split segment
status: done
dependencies: []
---

# Scope

- When a single chord crosses a row boundary and is rendered as two parts across two rows, show the chord label on whichever part is wider (by seconds), rather than always on the part containing the chord's start.

# Acceptance

- Given a chord that starts in row N and continues into row N+1 (or starts before a row and ends inside it), the label is rendered on the wider of the two visible parts; the other part stays blank but keeps the shared background color.
- Chords fully contained in one row are unaffected (label still shown on that single part).
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- The split logic lives in `buildChordRows` in `frontend/components/chord-track.tsx:39`. Today `showLabel` is set to `!chord.isSilence && chord.start >= row.rowStart` — i.e., the part containing the chord's start always wins (see `frontend/components/chord-track.tsx:59`). Replace that with a two-pass decision: first build all segments across rows, then for each chord that produced more than one segment pick the part with the larger `end - start` to carry the label.
- Keep the existing color-index inheritance so both parts of a split chord still share the same background (`chordColorIndices` in `frontend/components/chord-track.tsx:29`).
- Edge case to watch: a chord that starts before the first row's `rowStart` (chord.start < row.rowStart) currently renders its first part blank; under the new rule that first part may now win the label if it's the wider one. Confirm this is desirable via the wider-segment test, don't special-case it.
- Background per T0010 decision "Chord splitting across rows".

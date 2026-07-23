---
id: T0015
title: Fix doubled border between chord track and master track
status: done
dependencies: []
---

# Scope

- Eliminate the visually doubled 1px border that appears between the chord track's bottom edge and the master track's top edge when both tracks are present, which makes that seam look twice as thick as the other borders.
- The chord track is optional (`hasChords` may be false in `frontend/components/sheet-view.tsx:42`), so the seam only exists when chords are rendered. The fix must not add a stray missing-border artifact when only the master track is shown.

# Acceptance

- With chords present, the seam between the chord row and the master row is visually 1px — the same thickness as the other outer borders of the row block.
- With no chords, the master track's top border still renders (no missing border).
- `pnpm typecheck` and `pnpm lint` pass.

# Implementation Notes

- Source of the doubling: `ChordTrackRow` renders each segment with `border-y` (`frontend/components/chord-track.tsx:73-77`) and `MasterTrackRow`'s canvas carries `border border-primary/10` (`frontend/components/master-track.tsx:72`). Stacked, that's two 1px borders at the seam.
- Two candidate fixes — pick whichever is cleaner in practice:
  1. Drop the chord track's bottom border: replace `border-y` with `border-t` only on chord segments (no change to master). When `hasChords` is false the master's own `border` still draws the top, so no artifact. This is the user's suggested approach and is the simpler one.
  2. Use CSS border-collapse semantics (e.g., `-mt-px` on the master track to overlap the borders). Adds a nested-track margin coupling the two components that doesn't exist today — more invasive, avoid unless fix 1 has a downside.
- Prefer fix 1 unless implementation reveals a problem (e.g., the chord strip looks unbalanced without a bottom border). The user already noted the chord track may not exist, which fix 1 handles cleanly.
- Confirm the cursor overlay in `frontend/components/sheet-view.tsx:97-106` still spans both strips correctly after the change — it's positioned absolutely from the row block top, not from the chord strip bottom, so it should be unaffected.

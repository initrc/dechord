---
id: T0004
title: Benchmark madmom recognizer variants
status: done
dependencies:
  - T0001
---

# Scope

- Resolve open decision #3 in design-v1.md: pick between `DeepChromaChordRecognitionProcessor` (deep chroma + CRF) and `CRFChordRecognitionProcessor` (CNN chord features + CRF).
- Run both over a single song with a known chord progression (the user knows it from their DAW) and compare the two outputs against the known progression by eye. No hand-labeled ground-truth JSON — matching timestamps by hand is error-prone, and the user can verify the recognized chords directly.

# Acceptance

- A short script in `backend/benchmarks/recognizer_compare.py` runs both processors on the test song and prints each recognizer's chord progression.
- The result is written to `ravel/docs/recognizer-benchmark.md` with the chosen variant and the rationale (one paragraph each).
- Both variants are confirmed to emit maj/min/N only (per `recognizer-tradeoffs.md`).

# Implementation Notes

- Both processors return `(start, end, label)` tuples via `majmin_targets_to_chord_labels`; label space is identical (maj/min/N). The decision is purely empirical accuracy on the target music style.
- Test song: `backend/benchmarks/samples/suzume.mp3` (git-ignored). The user runs the script, reads both progressions, and verifies them against the known progression from their DAW.
- The benchmark is throwaway — it informs T0005 and is not part of the shipped product.
- If the outputs are roughly equally good (both about as close to the known progression), pick `DeepChromaChordRecognitionProcessor` as the default (smaller, older, well-cited).
- Reference: `ravel/docs/recognizer-tradeoffs.md`, `ravel/docs/design-v1.md` Open decisions.

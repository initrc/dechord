---
id: T0004
title: Benchmark madmom recognizer variants
status: new
dependencies:
  - T0001
---

# Scope

- Resolve open decision #3 in design-v1.md: pick between `DeepChromaChordRecognitionProcessor` (deep chroma + CRF) and `CRFChordRecognitionProcessor` (CNN chord features + CRF).
- Run both over a small held-out set (~5 songs with known chord annotations — hand-labeled is fine for this decision) and compare on a simple chord-accuracy metric (overlap-weighted chord label agreement, frame-level correctness).

# Acceptance

- A short script in `backend/benchmarks/recognizer_compare.py` runs both processors on the test set and prints per-song and aggregate accuracy.
- The result is written to `ravel/docs/recognizer-benchmark.md` with the chosen variant and the rationale (one paragraph each).
- Both variants are confirmed to emit maj/min/N only (per `recognizer-tradeoffs.md`).

# Implementation Notes

- Both processors return `(start, end, label)` tuples via `majmin_targets_to_chord_labels`; label space is identical (maj/min/N). The decision is purely empirical accuracy on the target music style.
- Test set: pick songs representative of what Dechord users will process. If the user mostly studies pop/rock, choose that; if jazz, acknowledge that maj/min/N is a poor fit either way and the benchmark is for tie-breaking only.
- The benchmark is throwaway — it informs T0005 and is not part of the shipped product.
- If the accuracy difference is within noise (a few points), pick `DeepChromaChordRecognitionProcessor` as the default (smaller, older, well-cited).
- Reference: `ravel/docs/recognizer-tradeoffs.md`, `ravel/docs/design-v1.md` Open decisions.
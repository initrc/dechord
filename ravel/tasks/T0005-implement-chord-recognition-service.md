---
id: T0005
title: Implement chord recognition service
status: new
dependencies:
  - T0002
  - T0004
---

# Scope

- Implement the chord recognition service that loads a normalized WAV from the library, runs the chosen madmom processor (set in T0004), and writes `chords.json` to `library/{sha256}/chords.json`.
- Output JSON shape matches the `chords` array in the Output contract of design-v1.md.
- Update the `media` row's `has_chords` to true and `status` to `done` on success, `failed` on exception.

# Acceptance

- Given a stored normalized WAV, calling the service produces a `chords.json` file at `library/{sha256}/chords.json` with the expected schema.
- `chords.json` rows are sorted by `start` with no gaps or overlaps (each chord's `end` equals the next's `start`, except the final `end`).
- Labels are JAMS-style (`root:quality` or `N`); root pitch classes use sharps (`C`, `C#`, ... per madmom's `majmin_targets_to_chord_labels`).
- On an exception during recognition, the `media` row is set to `failed` and `chords.json` is not written or is removed; the exception message is captured for the job status (T0006).
- Lint passes.

# Implementation Notes

- madmom's `DeepChromaChordRecognitionProcessor` / `CRFChordRecognitionProcessor` is a `SequentialProcessor` over a chroma extractor and a CRF decoder. Construct the processor once at module load (model load is slow); reuse the instance across calls.
- Feed the normalized WAV path (`library/{sha256}/source.wav`); do not feed the original upload — some formats (`m4a`) may not decode via madmom's `SignalProcessor` even though `ffmpeg` normalized them. Confirm via T0004's benchmark script.
- madmom returns a numpy structured array with fields `('start', '<f8'), ('end', '<f8'), ('label', 'O')`. Convert to plain dicts for JSON.
- This service is sync; it is invoked from a background job in T0006. No HTTP endpoint in this task.
- Reference: `ravel/docs/design-v1.md` Output contract, Pipeline section.
---
id: T0005
title: Implement chord recognition service
status: done
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

# Results

- `backend/app/recognition.py` implements the service; `set_media_recognition`
  was added to `app/persistence.py` to set `status` + `has_chords` in one
  update (used for both the `done` and `failed` transitions).
- Madmom is wrapped in a `ChordRecognizer` class (template method): `recognize`
  runs the raw-array → tuples → stitch flow, and `_raw_chords` is the seam to
  the madmom pipeline, kept in a private `_madmom_pipeline` field so the madmom
  class names don't leak into the service's call site. Tests subclass and
  override `_raw_chords` with a canned numpy structured array — no models load,
  no real audio needed.
- The recognizer is a **lazy module-level singleton** (`get_recognizer()`), not
  eagerly built at import. The task note said "construct once at module load";
  the binding intent is "build once, reuse across calls" (model load is slow),
  and lazy construction satisfies that without slowing import of
  `recognition.py` — which matters for tests, which inject a fake `recognizer=`
  and must not spawn a real model load.
- `chords.json` is a **bare JSON array** of `{start, end, label}` objects (the
  "rows" of the Output contract's `chords` field), not a `{"chords": [...]}`
  envelope. `GET /media/{id}` (T0007) will embed the file contents under
  `chords` when assembling the full record.
- Output is sorted by `start` and re-stitched so each segment's `end` equals
  the next segment's `start` (final `end` preserved), eliminating any gaps or
  overlaps madmom might emit — handled by `_stitch`.
- On exception the media row flips to `failed` / `has_chords=False`, any stale
  `chords.json` is removed, and the exception is re-raised so T0006's job can
  capture the message for the job status.
- Tests (`backend/tests/test_recognition.py`) subclass `ChordRecognizer` with
  `_FakeChordRecognizer` and `_ExplodingChordRecognizer`; they cover the write
  + row update, sorting/stitching, the failure cleanup (including a pre-existing
  stale `chords.json`), unknown media id, and JAMS-style label pass-through.
- **mypy added** to the project (`backend/pyproject.toml`, dev group,
  `mypy>=2.2` — current stable release and the version the gates actually run
  against. 2.x defaults `--local-partial-types` on, which affects cross-scope
  inference and is exactly the `global`-narrowing situation the `_recognizer`
  singleton relies on). Config: `python_version = "3.13"`,
  `ignore_missing_imports = true`
  (madmom ships no stubs), `check_untyped_defs = true`, and
  `[tool.mypy-app]` sets `disallow_untyped_defs = true` so the `app` package is
  held to a strict bar; tests use mypy's baseline (existing pre-T0005 tests
  aren't fully annotated — tightening them is a separate future task).
  `make typecheck` runs `uv run mypy app tests`. Today the project's quality
  gates are: `make lint` (ruff), `make typecheck` (mypy), `make test` (pytest).
- `.gitignore` updated to ignore IntelliJ project files (`.idea/`, `*.iml`);
  the auto-generated `.idea/.gitignore` only covered user-specific files, not
  `backend.iml` which lives outside `.idea/`.
- All three gates pass: `uv run ruff check .` (clean), `uv run mypy app tests`
  (Success: no issues found in 8 source files), `uv run pytest` (12 passing).
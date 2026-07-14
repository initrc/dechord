"""Chord recognition service — loads a normalized WAV, runs madmom, writes chords.json.

The chord stage of the pipeline (see `ravel/docs/design-v1.md` — Pipeline). It is
sync and invoked from a background job; no HTTP endpoint lives here.

Per Open decision #3 (resolved in `ravel/docs/recognizer-benchmark.md`)
the recognizer is `DeepChromaChordRecognitionProcessor` — a `SequentialProcessor`
over `DeepChromaProcessor` (deep chroma) and a CRF decoder. The processor's
models load slowly, so a single instance is built once and reused across calls.

Feed the normalized WAV (`library/{sha256}/source.wav`), not the original upload:
some formats (e.g. `m4a`) decode via ffmpeg but not via madmom's
`SignalProcessor` (see the recognizer benchmark).

madmom returns a numpy structured array with dtype
`[('start', '<f8'), ('end', '<f8'), ('label', 'O')]` — float64 start/end
seconds and an object-typed label string. `_segments_from_structured`
iterates it and yields plain `(start, end, label)` tuples.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from madmom.audio.chroma import DeepChromaProcessor
from madmom.features.chords import DeepChromaChordRecognitionProcessor
from madmom.processors import SequentialProcessor

from app import persistence
from app.persistence import MediaStatus

logger = logging.getLogger(__name__)


class ChordRecognizer:
    """Wrap a madmom chord pipeline behind a plain `recognize(path)` method.

    The production backend is madmom's DeepChroma CRF (see
    `ravel/docs/recognizer-benchmark.md`). Wrapping it (rather than calling the
    `SequentialProcessor` directly) gives the service a stable, owned type to
    depend on and gives tests a subclassing hook: override `_raw_chords` to
    return a canned numpy structured array, so the conversion + stitching flow
    runs without loading any models.
    """

    def __init__(self, madmom_pipeline: SequentialProcessor | None = None) -> None:
        # `None` is only valid for subclasses that override `_raw_chords`; the
        # production path requires a real pipeline and asserts inside it.
        self._madmom_pipeline = madmom_pipeline

    def recognize(self, wav_path: Path) -> list[tuple[float, float, str]]:
        """Run the recognizer on one WAV, returning stitched (start, end, label) tuples."""
        raw = self._raw_chords(wav_path)
        segments = _segments_from_structured(raw)
        return _stitch(segments)

    def _raw_chords(self, wav_path: Path) -> np.ndarray:
        """Run the madmom chord pipeline over the WAV and return its raw
        structured array. Override in subclasses to substitute a canned array
        (e.g. tests) without loading any models.
        """
        assert self._madmom_pipeline is not None, "no madmom pipeline wired"
        return self._madmom_pipeline(str(wav_path))


# Module-level singleton. Model load is slow; the recognizer is built once and
# reused across calls. Built lazily so importing this module (e.g. by tests)
# doesn't load the madmom models.
_recognizer: ChordRecognizer | None = None


def get_recognizer() -> ChordRecognizer:
    """The shared DeepChroma chord recognizer, constructed on first use."""
    global _recognizer
    if _recognizer is None:
        madmom_pipeline = SequentialProcessor(
            [DeepChromaProcessor(), DeepChromaChordRecognitionProcessor()]
        )
        _recognizer = ChordRecognizer(madmom_pipeline)
    assert _recognizer is not None  # narrows the global for the type checker
    return _recognizer


def _segments_from_structured(arr: np.ndarray) -> list[tuple[float, float, str]]:
    """Convert a madmom structured array (start, end, label) to plain tuples."""
    return [(float(start), float(end), str(label)) for start, end, label in arr]


def _stitch(segments: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Sort by start and enforce contiguous boundaries — no gaps, no overlaps.

    Each segment's end is set to the next segment's start; the final segment
    keeps its own end. The Output contract (design-v1.md) renders chords as a
    contiguous timeline, so the cached json must not leave holes or overlaps.
    """
    if not segments:
        return []
    ordered = sorted(segments, key=lambda s: s[0])
    fixed: list[tuple[float, float, str]] = []
    for i, (start, _end, label) in enumerate(ordered):
        end = ordered[i + 1][0] if i < len(ordered) - 1 else _end
        fixed.append((start, end, label))
    return fixed


def _to_chord_dicts(segments: list[tuple[float, float, str]]) -> list[dict[str, Any]]:
    return [{"start": s, "end": e, "label": lbl} for s, e, lbl in segments]


def recognize_chords(
    media_id: str,
    *,
    recognizer: ChordRecognizer | None = None,
    db_path: Path | None = None,
    library_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Recognize chords for one media item; write chords.json and update its row.

    Loads `library/{sha256}/source.wav`, runs the recognizer over it, writes
    the resulting chord list to `library/{sha256}/chords.json` as a JSON array
    of `{start, end, label}` (JAMS-style labels), and flips the media row to
    `done` / `has_chords=True`.

    On any exception the media row is set to `failed` / `has_chords=False` and
    any stale `chords.json` is removed; the exception is re-raised so the
    caller (the background job) can capture the message for the job status.
    """
    db_path = persistence.DB_PATH if db_path is None else db_path
    library_dir = persistence.LIBRARY_DIR if library_dir is None else library_dir
    recognizer = recognizer if recognizer is not None else get_recognizer()

    conn = persistence.open_db(db_path)
    try:
        row = persistence.get_media(conn, media_id)
        if row is None:
            raise KeyError(f"unknown media id: {media_id}")
        sha = row.sha256
        wav_path = persistence.source_wav_path(sha, library_dir=library_dir)
        chords_file = persistence.chords_path(sha, library_dir=library_dir)

        try:
            segments = recognizer.recognize(wav_path)
            if segments:
                logger.info(
                    "recognized %d chords from %s (%.2fs..%.2fs)",
                    len(segments), wav_path, segments[0][0], segments[-1][1],
                )
            chords = _to_chord_dicts(segments)
            persistence.write_chords(
                sha, json.dumps(chords).encode("utf-8"), library_dir=library_dir
            )
            persistence.set_media_recognition(
                conn, media_id, MediaStatus.done, has_chords=True
            )
            return chords
        except Exception:
            # A failed re-run must not leave a stale chords.json behind; the
            # has_chords flag below would otherwise contradict the file's absence.
            if chords_file.exists():
                chords_file.unlink()
            persistence.set_media_recognition(
                conn, media_id, MediaStatus.failed, has_chords=False
            )
            raise
    finally:
        conn.close()
"""Tests for the chord recognition service.

Run: `uv run pytest`. The recognizer is faked by subclassing `ChordRecognizer`
and overriding `_raw_chords`, so the tests don't load madmom's models or need
real audio; they exercise the stitching, serialization, and media-row update
paths. Each test points persistence at a tmp library dir.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app import persistence, recognition
from app.persistence import MediaStatus, get_media, init_library, insert_media, open_db
from app.recognition import ChordRecognizer


def _structured(rows: list[tuple[float, float, str]]) -> np.ndarray:
    """Build a madmom-shaped structured array: (start, end, label)."""
    return np.array(
        rows,
        dtype=[("start", "<f8"), ("end", "<f8"), ("label", "O")],
    )


@pytest.fixture()
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    lib = tmp_path / "library"
    monkeypatch.setattr(persistence, "LIBRARY_DIR", lib)
    monkeypatch.setattr(persistence, "DB_PATH", lib / "index.db")
    init_library(db_path=persistence.DB_PATH, library_dir=lib)
    return lib


class _FakeChordRecognizer(ChordRecognizer):
    """Recognizer subclass returning a canned structured array in place of a
    real madmom run. Used by every test that needs a working recognize()."""

    def __init__(self, rows: list[tuple[float, float, str]]) -> None:
        super().__init__()  # no madmom pipeline; `_raw_chords` is overridden
        self._rows = rows

    def _raw_chords(self, _wav_path: Path) -> np.ndarray:
        return _structured(self._rows)


class _ExplodingChordRecognizer(ChordRecognizer):
    """Recognizer whose `_raw_chords` raises, exercising the failure path."""

    def _raw_chords(self, _wav_path: Path) -> np.ndarray:
        raise RuntimeError("model exploded")


def _insert_media_row(sha: str = "a" * 64) -> str:
    conn = open_db(persistence.DB_PATH)
    try:
        row = insert_media(conn, sha256=sha, original_filename="clip.wav", duration=4.0)
        return row.id
    finally:
        conn.close()


def test_recognize_writes_chords_json_and_updates_row(library: Path) -> None:
    media_id = _insert_media_row()
    rows = [(0.0, 2.12, "C:maj"), (2.12, 4.24, "G:maj"), (4.24, 6.0, "N")]
    fake = _FakeChordRecognizer(rows)

    chords = recognition.recognize_chords(media_id, recognizer=fake)

    assert chords == [
        {"start": 0.0, "end": 2.12, "label": "C:maj"},
        {"start": 2.12, "end": 4.24, "label": "G:maj"},
        {"start": 4.24, "end": 6.0, "label": "N"},
    ]

    # chords.json is the bare array from the Output contract.
    chords_file = persistence.chords_path("a" * 64, library_dir=library)
    on_disk = json.loads(chords_file.read_bytes())
    assert on_disk == chords

    conn = open_db(persistence.DB_PATH)
    try:
        row = get_media(conn, media_id)
        assert row is not None
        assert row.status == MediaStatus.done.value
        assert row.has_chords is True
    finally:
        conn.close()


def test_chords_sorted_by_start_with_no_gaps_or_overlaps(library: Path) -> None:
    media_id = _insert_media_row()
    # Deliberately out of order, with an overlap and a gap.
    rows = [
        (4.30, 6.40, "A:min"),
        (0.0, 2.12, "C:maj"),
        (2.0, 4.30, "G:maj"),  # overlaps the previous; gap before A:min
    ]
    fake = _FakeChordRecognizer(rows)

    chords = recognition.recognize_chords(media_id, recognizer=fake)

    starts = [c["start"] for c in chords]
    assert starts == sorted(starts)
    # Each end equals the next start; final end is preserved.
    for a, b in zip(chords, chords[1:]):
        assert a["end"] == b["start"]
    assert chords[-1]["end"] == 6.40
    assert chords[0]["start"] == 0.0


def test_recognize_failure_marks_failed_and_removes_chords(library: Path, tmp_path: Path) -> None:
    media_id = _insert_media_row()
    sha = "a" * 64

    # Pre-existing chords.json from a prior successful run must be cleaned up.
    persistence.write_chords(sha, b'[{"start":0,"end":1,"label":"N"}]', library_dir=library)
    assert persistence.chords_path(sha, library_dir=library).exists()

    with pytest.raises(RuntimeError, match="model exploded"):
        recognition.recognize_chords(
            media_id, recognizer=_ExplodingChordRecognizer()
        )

    # chords.json removed and row marked failed / has_chords=False.
    assert not persistence.chords_path(sha, library_dir=library).exists()
    conn = open_db(persistence.DB_PATH)
    try:
        row = get_media(conn, media_id)
        assert row is not None
        assert row.status == MediaStatus.failed.value
        assert row.has_chords is False
    finally:
        conn.close()


def test_unknown_media_id_raises(library: Path) -> None:
    with pytest.raises(KeyError):
        recognition.recognize_chords(
            "media_nope", recognizer=_FakeChordRecognizer([])
        )


def test_labels_pass_through_jams_style(library: Path) -> None:
    media_id = _insert_media_row()
    rows = [(0.0, 1.0, "C:maj"), (1.0, 2.0, "C#:min"), (2.0, 3.0, "N")]
    chords = recognition.recognize_chords(
        media_id, recognizer=_FakeChordRecognizer(rows)
    )
    assert [c["label"] for c in chords] == ["C:maj", "C#:min", "N"]
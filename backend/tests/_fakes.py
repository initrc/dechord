"""Shared test doubles and helpers for the backend test suite.

Centralizes the fakes that recur across test_recognition.py, test_jobs.py, and
test_uploads.py: a configurable chord recognizer (no madmom models load, no
real audio needed), an exploding variant for failure paths, and small helpers
for inserting a media row, writing a placeholder source.wav, synthesizing a
minimal valid WAV, and building a TestClient with a fake recognizer patched in.

The recognizer fakes subclass `ChordRecognizer` and override `_raw_chords` —
the seam used by the recognition tests — so the conversion + stitching flow
in `recognition.py` runs without loading any models.
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

import numpy as np
import pytest
from starlette.testclient import TestClient

from app import main, persistence, recognition
from app.recognition import ChordRecognizer

# Default rows reused by upload/job tests that just need any successful chord.
DEFAULT_CHORD_ROWS: list[tuple[float, float, str]] = [(0.0, 0.5, "N")]


def structured_array(rows: list[tuple[float, float, str]]) -> np.ndarray:
    """Build a madmom-shaped structured array: (start, end, label)."""
    return np.array(rows, dtype=[("start", "<f8"), ("end", "<f8"), ("label", "O")])


class FakeChordRecognizer(ChordRecognizer):
    """Recognizer that returns a canned structured array instead of running madmom.

    Override of `_raw_chords` substitutes a pre-built array — used both directly
    (recognition tests) and as the patched `get_recognizer()` return value
    (upload/job tests, where Starlette's TestClient runs background tasks to
    completion before returning the response).
    """

    def __init__(self, rows: list[tuple[float, float, str]]) -> None:
        super().__init__()
        self._rows = rows

    def _raw_chords(self, wav_path: Path) -> np.ndarray:
        return structured_array(self._rows)


class ExplodingChordRecognizer(ChordRecognizer):
    """Recognizer whose `_raw_chords` raises, exercising the failure path.

    `recognize_chords` re-raises, so the job runner catches, marks the job
    `failed`, and records the message. The default message is matched by tests.
    """

    def _raw_chords(self, wav_path: Path) -> np.ndarray:
        raise RuntimeError("model exploded")


def insert_media_row(
    sha: str = "a" * 64,
    *,
    original_filename: str = "clip.wav",
    duration: float = 4.0,
) -> str:
    """Insert a `queued` media row and return its id.

    Uses the module-level `persistence.DB_PATH`; the `library` fixture
    (in conftest.py) monkeypatches it to a tmp dir.
    """
    conn = persistence.open_db(persistence.DB_PATH)
    try:
        row = persistence.insert_media(
            conn, sha256=sha, original_filename=original_filename, duration=duration
        )
        return row.id
    finally:
        conn.close()


def make_source_wav(sha: str, library: Path) -> None:
    """Write a placeholder `source.wav` under `library/{sha}/`.

    The fakes ignore the bytes; only the path's existence matters for
    `recognize_chords`, which resolves the WAV path from the media row's sha256.
    """
    (library / sha).mkdir(parents=True, exist_ok=True)
    (library / sha / "source.wav").write_bytes(b"RIFF\x00")


def make_wav_bytes(seconds: float = 0.5) -> bytes:
    """A minimal valid mono 16-bit PCM WAV; ffmpeg-normalizable.

    Synthesizes an upload without a fixture file on disk. Stdlib `wave` writes
    into an in-memory buffer so callers can both POST the bytes and write them
    to a path if a path is needed.
    """
    rate = 44100
    n_frames = int(rate * seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n_frames)
    return buf.getvalue()


def client_with_fake_recognizer(
    monkeypatch: pytest.MonkeyPatch,
    recognizer: ChordRecognizer | None = None,
) -> TestClient:
    """A TestClient with `recognition.get_recognizer` patched to a fake.

    The default fake returns `DEFAULT_CHORD_ROWS`; pass a custom recognizer
    (e.g. `ExplodingChordRecognizer`) for failure-path tests. Pairs with the
    `library` fixture, which must run first so DB/library paths are tmp-scoped.
    """
    if recognizer is None:
        recognizer = FakeChordRecognizer(DEFAULT_CHORD_ROWS)
    monkeypatch.setattr(recognition, "get_recognizer", lambda: recognizer)
    return TestClient(main.app)
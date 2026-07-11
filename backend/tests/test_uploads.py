"""Tests for the `POST /media` upload endpoint.

Run: `uv run pytest` (or `make test`). Each test points the persistence module
at a tmp library dir so the repo's `library/` is never touched. A small valid
WAV is synthesized with stdlib `wave` so the ffmpeg normalization step has real
audio to read; ffmpeg must be on PATH (documented prereq in backend/README.md).
"""

from __future__ import annotations

import wave

import pytest
from starlette.testclient import TestClient

from app import main, persistence


@pytest.fixture()
def client(tmp_path, monkeypatch):
    library = tmp_path / "library"
    monkeypatch.setattr(persistence, "LIBRARY_DIR", library)
    monkeypatch.setattr(persistence, "DB_PATH", library / "index.db")
    # TestClient without `with` skips lifespan startup (which would init the
    # module-default library dir). ingest_upload opens its own DB connection.
    return TestClient(main.app)


def _make_wav(path, seconds: float = 0.5) -> bytes:
    """A minimal valid mono 16-bit PCM WAV; ffmpeg-normalizable."""
    rate = 44100
    n_frames = int(rate * seconds)
    frames = b"\x00\x00" * n_frames
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)
    return path.read_bytes()


def test_upload_valid_returns_id_and_stores_files(client, tmp_path):
    library = persistence.LIBRARY_DIR
    wav_bytes = _make_wav(tmp_path / "clip.wav")

    resp = client.post(
        "/media",
        files={"file": ("clip.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201
    media_id = resp.json()["id"]
    assert media_id.startswith("media_")

    # Original content-hash-addressed file and normalized WAV are both stored.
    from app.persistence import get_media, open_db

    conn = open_db(persistence.DB_PATH)
    try:
        row = get_media(conn, media_id)
        assert row is not None
        assert row.sha256 and row.sha256 != ""
        assert row.original_filename == "clip.wav"
        assert row.status == "done"
        assert (library / f"{row.sha256}.wav").read_bytes() == wav_bytes
        assert (library / row.sha256 / "source.wav").exists()
    finally:
        conn.close()


def test_byte_identical_upload_dedups(client, tmp_path):
    wav_bytes = _make_wav(tmp_path / "clip.wav")

    first = client.post("/media", files={"file": ("clip.wav", wav_bytes, "audio/wav")})
    second = client.post("/media", files={"file": ("clip.wav", wav_bytes, "audio/wav")})
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    from app.persistence import list_media, open_db

    conn = open_db(persistence.DB_PATH)
    try:
        assert len(list_media(conn)) == 1
    finally:
        conn.close()


def test_oversized_upload_returns_413(client, tmp_path):
    # 1 MB over the limit.
    big = b"\x00" * (50 * 1024 * 1024 + 1)
    resp = client.post("/media", files={"file": ("big.wav", big, "audio/wav")})
    assert resp.status_code == 413


def test_unsupported_format_returns_415(client, tmp_path):
    resp = client.post(
        "/media", files={"file": ("notes.txt", b"hi", "text/plain")}
    )
    assert resp.status_code == 415

    # A second disallowed extension (.ogg) also returns 415.
    resp_mp3 = client.post(
        "/media", files={"file": ("clip.ogg", b"\x00", "audio/ogg")}
    )
    assert resp_mp3.status_code == 415
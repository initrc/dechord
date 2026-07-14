"""Tests for the `POST /media` upload endpoint.

Run: `uv run pytest` (or `make test`). Each test uses the shared `library`
fixture (conftest.py) so the repo's `library/` is never touched. A minimal
valid WAV is synthesized with stdlib `wave` (via `make_wav_bytes`) so the ffmpeg
normalization step has real audio to read; ffmpeg must be on PATH (documented
prereq in backend/README.md).

`POST /media` queues a recognition job as a FastAPI background task. Starlette's
TestClient runs background tasks to completion before returning the response, so
the `client` fixture patches in a fake recognizer to keep the tests fast and
offline (no madmom model load, no real recognition).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app import persistence
from app.persistence import get_media, list_media, open_db
from tests._fakes import client_with_fake_recognizer, make_wav_bytes


@pytest.fixture()
def client(library, monkeypatch) -> TestClient:
    # The `library` fixture (conftest.py) scopes DB/library to tmp; the fake
    # recognizer keeps the background task from loading madmom.
    return client_with_fake_recognizer(monkeypatch)


def test_upload_valid_returns_id_and_stores_files(client, tmp_path):
    library = persistence.LIBRARY_DIR
    wav_bytes = make_wav_bytes()
    (tmp_path / "clip.wav").write_bytes(wav_bytes)

    resp = client.post(
        "/media",
        files={"file": ("clip.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201
    media_id = resp.json()["id"]
    assert media_id.startswith("media_")
    # A fresh upload queues a recognition job; its id is returned for polling.
    job_id = resp.json()["job_id"]
    assert job_id.startswith("job_")

    # Original content-hash-addressed file and normalized WAV are both stored.
    conn = open_db(persistence.DB_PATH)
    try:
        row = get_media(conn, media_id)
        assert row is not None
        assert row.sha256 and row.sha256 != ""
        assert row.original_filename == "clip.wav"
        # The background task (fake recognizer) has run to completion by the
        # time TestClient returns, so the media row is `done` with chords.
        assert row.status == "done"
        assert row.has_chords is True
        assert (library / f"{row.sha256}.wav").read_bytes() == wav_bytes
        assert (library / row.sha256 / "source.wav").exists()
    finally:
        conn.close()


def test_byte_identical_upload_dedups(client, tmp_path):
    wav_bytes = make_wav_bytes()

    first = client.post("/media", files={"file": ("clip.wav", wav_bytes, "audio/wav")})
    second = client.post("/media", files={"file": ("clip.wav", wav_bytes, "audio/wav")})
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    # Dedup does not re-queue a job.
    assert "job_id" not in second.json()

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
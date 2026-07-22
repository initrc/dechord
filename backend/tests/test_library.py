"""Tests for the library read endpoints: GET /media, GET /media/{id},
GET /media/{id}/audio/source, POST /media/{id}/chords.

Run: `uv run pytest`. Each test uses the shared `library` fixture (conftest.py)
so the repo's `library/` is never touched. The recognizer is faked (see
`_fakes.py`) so no madmom models load and no real audio is needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app import persistence
from app.persistence import get_media, open_db
from tests._fakes import (
    DEFAULT_CHORD_ROWS,
    client_with_fake_recognizer,
    make_wav_bytes,
)


@pytest.fixture()
def client(library, monkeypatch) -> TestClient:
    return client_with_fake_recognizer(monkeypatch)


def _upload_wav(client: TestClient, filename: str = "clip.wav") -> str:
    wav_bytes = make_wav_bytes()
    resp = client.post(
        "/media",
        files={"file": (filename, wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_list_media_empty(client: TestClient) -> None:
    resp = client.get("/media")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_media_after_upload(client: TestClient) -> None:
    media_id = _upload_wav(client)

    resp = client.get("/media")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert item["id"] == media_id
    assert item["original_filename"] == "clip.wav"
    assert item["uploaded_at"]
    assert item["status"] == "done"
    assert item["has_chords"] is True


def test_get_media_detail(client: TestClient) -> None:
    media_id = _upload_wav(client)

    resp = client.get(f"/media/{media_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == media_id
    assert body["status"] == "done"
    assert body["audio"]["sample_rate"] == 44100
    assert abs(body["audio"]["duration"] - 0.5) < 0.01
    assert body["audio"]["source_path"].endswith(".wav")
    assert len(body["chords"]) == len(DEFAULT_CHORD_ROWS)
    chord = body["chords"][0]
    assert "start" in chord
    assert "end" in chord
    assert "label" in chord


def test_get_media_detail_404(client: TestClient) -> None:
    resp = client.get("/media/media_nope")
    assert resp.status_code == 404


def test_get_audio_source(client: TestClient) -> None:
    media_id = _upload_wav(client)

    resp = client.get(f"/media/{media_id}/audio/source")
    assert resp.status_code == 200
    assert "wav" in resp.headers["content-type"]
    assert len(resp.content) > 0


def test_get_audio_source_404(client: TestClient) -> None:
    resp = client.get("/media/media_nope/audio/source")
    assert resp.status_code == 404


def test_get_audio_peaks(client: TestClient) -> None:
    media_id = _upload_wav(client)

    resp = client.get(f"/media/{media_id}/audio/peaks")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"
    # Each peak is a float32 (4 bytes). For a 0.5s source at 44100 Hz with
    # 1000 peaks/sec the bucket size is 44 samples → 500 full buckets, so
    # the body's byte length is 4 * n_peaks.
    assert len(resp.content) % 4 == 0
    assert len(resp.content) > 0


def test_get_audio_peaks_404(client: TestClient) -> None:
    # Unknown media id → 404 for the media lookup, before the peaks file check.
    resp = client.get("/media/media_nope/audio/peaks")
    assert resp.status_code == 404


def test_get_audio_peaks_404_when_file_missing(
    client: TestClient, library: Path
) -> None:
    media_id = _upload_wav(client)

    conn = open_db(persistence.DB_PATH)
    try:
        row = get_media(conn, media_id)
        assert row is not None
        peaks_path = persistence.peaks_path(row.sha256, library_dir=persistence.LIBRARY_DIR)
    finally:
        conn.close()
    peaks_path.unlink()

    resp = client.get(f"/media/{media_id}/audio/peaks")
    assert resp.status_code == 404


def test_rerun_chords(client: TestClient) -> None:
    media_id = _upload_wav(client)

    resp = client.post(f"/media/{media_id}/chords")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"].startswith("job_")

    job_id = body["job_id"]
    job_resp = client.get(f"/jobs/{job_id}")
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "done"
    assert job_resp.json()["media_id"] == media_id


def test_rerun_chords_404(client: TestClient) -> None:
    resp = client.post("/media/media_nope/chords")
    assert resp.status_code == 404


def test_rerun_chords_sets_media_to_recognizing(library: Path, monkeypatch) -> None:
    """Verify the media row transitions to `recognizing` during re-recognition."""
    from tests._fakes import ExplodingChordRecognizer

    client = client_with_fake_recognizer(monkeypatch, ExplodingChordRecognizer())

    wav_bytes = make_wav_bytes()
    resp = client.post(
        "/media",
        files={"file": ("clip.wav", wav_bytes, "audio/wav")},
    )
    assert resp.status_code == 201
    media_id = resp.json()["id"]

    conn = open_db(persistence.DB_PATH)
    try:
        row = get_media(conn, media_id)
        assert row is not None
        assert row.status == "failed"
    finally:
        conn.close()

    resp = client.post(f"/media/{media_id}/chords")
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    job_resp = client.get(f"/jobs/{job_id}")
    assert job_resp.json()["status"] == "failed"

"""Tests for the async job runner and `GET /jobs/{id}`.

Run: `uv run pytest`. The recognizer is faked (see `_fakes.py`) so no madmom
models load and no real audio is needed. Each test uses the shared `library`
fixture (conftest.py) so the repo's `library/` is never touched.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app import jobs, persistence
from app.persistence import MediaStatus, get_job, get_media, insert_job, open_db
from app.recognition import ChordRecognizer
from tests._fakes import (
    DEFAULT_CHORD_ROWS,
    ExplodingChordRecognizer,
    FakeChordRecognizer,
    client_with_fake_recognizer,
    insert_media_row,
    make_source_wav,
    make_wav_bytes,
    structured_array,
)

DEFAULT_SHA = "a" * 64


class _ObservingChordRecognizer(ChordRecognizer):
    """Captures the job/media state mid-recognition to verify the
    `recognizing` transition happens before the recognizer runs."""

    job_id: str = ""
    media_id: str = ""
    job_status: str | None = None
    job_progress: int | None = None
    media_status: str | None = None

    def _raw_chords(self, wav_path: Path) -> np.ndarray:
        conn = open_db(persistence.DB_PATH)
        try:
            job = get_job(conn, self.job_id)
            media = get_media(conn, self.media_id)
        finally:
            conn.close()
        assert job is not None and media is not None
        self.job_status = job.status
        self.job_progress = job.progress
        self.media_status = media.status
        return structured_array(DEFAULT_CHORD_ROWS)


def _setup_job() -> tuple[str, str]:
    """Insert a media row + a queued job row, returning (job_id, media_id)."""
    media_id = insert_media_row()
    conn = open_db(persistence.DB_PATH)
    try:
        job = insert_job(conn, media_id=media_id)
    finally:
        conn.close()
    return job.id, media_id


def test_run_job_transitions_queued_to_done(library: Path) -> None:
    make_source_wav(DEFAULT_SHA, library)
    job_id, media_id = _setup_job()
    conn = open_db(persistence.DB_PATH)
    try:
        job = get_job(conn, job_id)
        assert job is not None
        assert job.status == MediaStatus.queued
        assert job.progress == 0
    finally:
        conn.close()

    jobs.run_recognition_job(
        job_id, media_id, recognizer=FakeChordRecognizer([(0.0, 2.0, "C:maj")])
    )

    conn = open_db(persistence.DB_PATH)
    try:
        done = get_job(conn, job_id)
        assert done is not None
        assert done.status == MediaStatus.done
        assert done.progress == 100
        assert done.error is None
        media = get_media(conn, media_id)
        assert media is not None
        assert media.status == MediaStatus.done
        assert media.has_chords is True
    finally:
        conn.close()


def test_run_job_sets_recognizing_before_recognizer_runs(library: Path) -> None:
    make_source_wav(DEFAULT_SHA, library)
    job_id, media_id = _setup_job()

    fake = _ObservingChordRecognizer()
    fake.job_id = job_id
    fake.media_id = media_id
    jobs.run_recognition_job(job_id, media_id, recognizer=fake)

    # Mid-recognition the job was `recognizing` at 50 and the media was too.
    assert fake.job_status == MediaStatus.recognizing
    assert fake.job_progress == 50
    assert fake.media_status == MediaStatus.recognizing


def test_run_job_failure_sets_failed_with_error(library: Path) -> None:
    make_source_wav(DEFAULT_SHA, library)
    job_id, media_id = _setup_job()

    jobs.run_recognition_job(job_id, media_id, recognizer=ExplodingChordRecognizer())

    conn = open_db(persistence.DB_PATH)
    try:
        failed = get_job(conn, job_id)
        assert failed is not None
        assert failed.status == MediaStatus.failed
        assert failed.error == "model exploded"
        media = get_media(conn, media_id)
        assert media is not None
        assert media.status == MediaStatus.failed
        assert media.has_chords is False
    finally:
        conn.close()


def test_get_jobs_endpoint_returns_queued_job(
    library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id, media_id = _setup_job()

    client = client_with_fake_recognizer(
        monkeypatch, FakeChordRecognizer(DEFAULT_CHORD_ROWS)
    )
    resp = client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == MediaStatus.queued
    assert body["progress"] == 0
    assert body["media_id"] == media_id
    assert body["error"] is None


def test_get_jobs_endpoint_404_for_unknown_job(
    library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = client_with_fake_recognizer(monkeypatch)
    resp = client.get("/jobs/job_nope")
    assert resp.status_code == 404


def test_post_media_then_get_job_is_done(
    library: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: POST /media returns job_id; after the background task
    completes, GET /jobs/{id} reports done with progress 100."""
    client = client_with_fake_recognizer(
        monkeypatch, FakeChordRecognizer(DEFAULT_CHORD_ROWS)
    )

    resp = client.post(
        "/media",
        files={"file": ("clip.wav", make_wav_bytes(), "audio/wav")},
    )
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]

    job_resp = client.get(f"/jobs/{job_id}")
    assert job_resp.status_code == 200
    body = job_resp.json()
    assert body["status"] == MediaStatus.done
    assert body["progress"] == 100
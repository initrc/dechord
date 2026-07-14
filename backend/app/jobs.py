"""Async job runner for chord recognition.

FastAPI `BackgroundTasks` drive the chord stage: a `job` row tracks progress
through `queued → recognizing → done | failed`, and `recognize_chords` does
the actual work and updates the `media` row. See `ravel/docs/design-v1.md`
Backend — one process, in-process background tasks, adequate for single-user
local use; a real queue (arq + Redis) is deferred.

Progress is coarse (per the task notes): 0 at queue time, 50 at recognizing
start, 100 at done. Fine-grained per-frame progress would require hooking into
madmom's processor and is deferred.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app import persistence, recognition
from app.persistence import MediaStatus
from app.recognition import ChordRecognizer

logger = logging.getLogger(__name__)


def run_recognition_job(
    job_id: str,
    media_id: str,
    *,
    recognizer: ChordRecognizer | None = None,
    db_path: Path | None = None,
    library_dir: Path | None = None,
) -> None:
    """Background task: drive one chord recognition job to completion.

    Transitions the job row `queued → recognizing → done | failed` and delegates
    the recognition work (and the media-row `recognizing → done | failed` flip)
    to `recognize_chords`. On failure the exception message is captured on the
    job row; the exception is not re-raised — the job status is the record.
    """
    db_path = persistence.DB_PATH if db_path is None else db_path
    library_dir = persistence.LIBRARY_DIR if library_dir is None else library_dir

    conn = persistence.open_db(db_path)
    try:
        persistence.update_job(conn, job_id, status=MediaStatus.recognizing, progress=50)
        persistence.update_media_status(conn, media_id, MediaStatus.recognizing)
    finally:
        conn.close()

    try:
        recognition.recognize_chords(
            media_id, recognizer=recognizer, db_path=db_path, library_dir=library_dir
        )
    except Exception as exc:
        # recognize_chords already flipped the media row to `failed`; record
        # the failure on the job row and stop. The message is what GET /jobs/{id}
        # surfaces to the frontend.
        logger.exception(
            "chord recognition job %s failed for media %s", job_id, media_id
        )
        conn = persistence.open_db(db_path)
        try:
            persistence.update_job(conn, job_id, status=MediaStatus.failed, error=str(exc))
        finally:
            conn.close()
        return

    conn = persistence.open_db(db_path)
    try:
        persistence.update_job(conn, job_id, status=MediaStatus.done, progress=100)
    finally:
        conn.close()

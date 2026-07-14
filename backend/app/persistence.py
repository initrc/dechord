"""SQLite index and on-disk content storage for the media library.

Layout (see ravel/docs/design-v1.md — Media library):

    library/
      {sha256}.{ext}        # original upload, content-hash addressed
      {sha256}/
        chords.json         # cached recognition result

The SQLite index `library/index.db` holds one row per media item. Storage is
flat (no two-char hash prefix directory) and content-hash addressed so that the
same byte-identical upload dedups to one record.
"""

from __future__ import annotations

import secrets
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

LIBRARY_DIR = Path("library")
DB_PATH = LIBRARY_DIR / "index.db"

# Single-statement v1 schema. Evolve into a real migration step only when a
# column changes; until then `CREATE TABLE IF NOT EXISTS` is idempotent and
# sufficient for restart-without-error.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS media (
    id                TEXT PRIMARY KEY,
    sha256            TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    uploaded_at       TEXT NOT NULL,
    duration          REAL,
    status            TEXT NOT NULL,
    has_chords        INTEGER NOT NULL DEFAULT 0
)
"""

# Job table. `stage` is reserved for future siblings (beats, key);
# v1 has only `chords`. `status`/`progress` mirror the media lifecycle but
# track the job itself. `error` is populated only on `failed`.
JOB_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS job (
    id          TEXT PRIMARY KEY,
    media_id    TEXT NOT NULL,
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL,
    progress    INTEGER NOT NULL DEFAULT 0,
    error       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY (media_id) REFERENCES media(id)
)
"""


class MediaStatus(str, Enum):
    """Lifecycle of a media item's chord recognition. Matches `GET /jobs/{id}`."""

    queued = "queued"
    recognizing = "recognizing"
    done = "done"
    failed = "failed"


@dataclass(frozen=True)
class MediaRow:
    id: str
    sha256: str
    original_filename: str
    uploaded_at: str
    duration: float | None
    status: str
    has_chords: bool


@dataclass(frozen=True)
class JobRow:
    id: str
    media_id: str
    stage: str
    status: str
    progress: int
    error: str | None
    created_at: str
    updated_at: str


def new_media_id() -> str:
    """Short, unique row id. Distinct from `sha256` (which is content addressing)."""
    return "media_" + secrets.token_hex(4)  # 8 hex chars


def new_job_id() -> str:
    """Short, unique job id. Mirrors the `media_` convention."""
    return "job_" + secrets.token_hex(4)  # 8 hex chars


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_library(library_dir: Path = LIBRARY_DIR) -> None:
    library_dir.mkdir(parents=True, exist_ok=True)


def open_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the index DB and ensure the `media` and `job` tables exist (idempotent)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA_SQL)
    conn.execute(JOB_SCHEMA_SQL)
    return conn


def init_library(db_path: Path = DB_PATH, library_dir: Path = LIBRARY_DIR) -> None:
    """Startup migration: create the library dir and the `media` table if missing."""
    ensure_library(library_dir)
    open_db(db_path).close()


def _row_from_record(record: sqlite3.Row) -> MediaRow:
    return MediaRow(
        id=record["id"],
        sha256=record["sha256"],
        original_filename=record["original_filename"],
        uploaded_at=record["uploaded_at"],
        duration=record["duration"],
        status=record["status"],
        has_chords=bool(record["has_chords"]),
    )


def insert_media(
    conn: sqlite3.Connection,
    *,
    sha256: str,
    original_filename: str,
    duration: float | None = None,
    status: MediaStatus = MediaStatus.queued,
    has_chords: bool = False,
) -> MediaRow:
    """Insert a media row, returning the stored record (generates id + timestamp)."""
    row = MediaRow(
        id=new_media_id(),
        sha256=sha256,
        original_filename=original_filename,
        uploaded_at=now_iso(),
        duration=duration,
        status=status,
        has_chords=has_chords,
    )
    conn.execute(
        "INSERT INTO media "
        "(id, sha256, original_filename, uploaded_at, duration, status, has_chords) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (row.id, row.sha256, row.original_filename, row.uploaded_at,
         row.duration, row.status, int(row.has_chords)),
    )
    conn.commit()
    return row


def get_media(conn: sqlite3.Connection, media_id: str) -> MediaRow | None:
    cur = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,))
    record = cur.fetchone()
    return _row_from_record(record) if record else None


def get_media_by_sha256(conn: sqlite3.Connection, sha256: str) -> MediaRow | None:
    """Existing record for content hash, or None. Powers upload dedup."""
    cur = conn.execute("SELECT * FROM media WHERE sha256 = ?", (sha256,))
    record = cur.fetchone()
    return _row_from_record(record) if record else None


def update_media_status(
    conn: sqlite3.Connection, media_id: str, status: MediaStatus
) -> MediaRow:
    conn.execute(
        "UPDATE media SET status = ? WHERE id = ?", (status.value, media_id)
    )
    conn.commit()
    row = get_media(conn, media_id)
    if row is None:
        raise KeyError(media_id)
    return row


def set_media_recognition(
    conn: sqlite3.Connection,
    media_id: str,
    status: MediaStatus,
    *,
    has_chords: bool,
) -> MediaRow:
    """Set both the recognition status and the has_chords flag in one update.

    Used by the chord recognition service: `done` + `has_chords=True` on
    success, `failed` + `has_chords=False` on exception (the cached
    `chords.json` is removed alongside, so the flag must not stay stale).
    """
    conn.execute(
        "UPDATE media SET status = ?, has_chords = ? WHERE id = ?",
        (status.value, int(has_chords), media_id),
    )
    conn.commit()
    row = get_media(conn, media_id)
    if row is None:
        raise KeyError(media_id)
    return row


def list_media(conn: sqlite3.Connection) -> list[MediaRow]:
    cur = conn.execute("SELECT * FROM media ORDER BY uploaded_at DESC")
    return [_row_from_record(r) for r in cur.fetchall()]


# --- job rows ----------------------------------------------------------------

def _job_from_record(record: sqlite3.Row) -> JobRow:
    return JobRow(
        id=record["id"],
        media_id=record["media_id"],
        stage=record["stage"],
        status=record["status"],
        progress=record["progress"],
        error=record["error"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )


def insert_job(
    conn: sqlite3.Connection,
    *,
    media_id: str,
    stage: str = "chords",
    progress: int = 0,
) -> JobRow:
    """Insert a `queued` job row, returning the stored record (generates id + timestamps)."""
    ts = now_iso()
    row = JobRow(
        id=new_job_id(),
        media_id=media_id,
        stage=stage,
        status=MediaStatus.queued.value,
        progress=progress,
        error=None,
        created_at=ts,
        updated_at=ts,
    )
    conn.execute(
        "INSERT INTO job "
        "(id, media_id, stage, status, progress, error, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (row.id, row.media_id, row.stage, row.status, row.progress,
         row.error, row.created_at, row.updated_at),
    )
    conn.commit()
    return row


def get_job(conn: sqlite3.Connection, job_id: str) -> JobRow | None:
    cur = conn.execute("SELECT * FROM job WHERE id = ?", (job_id,))
    record = cur.fetchone()
    return _job_from_record(record) if record else None


def update_job(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    status: MediaStatus | None = None,
    progress: int | None = None,
    error: str | None = None,
) -> JobRow:
    """Update a subset of job fields and bump `updated_at`. Raises KeyError if missing."""
    sets: list[str] = []
    params: list[object] = []
    if status is not None:
        sets.append("status = ?")
        params.append(status.value)
    if progress is not None:
        sets.append("progress = ?")
        params.append(progress)
    if error is not None:
        sets.append("error = ?")
        params.append(error)
    sets.append("updated_at = ?")
    params.append(now_iso())
    params.append(job_id)
    conn.execute(f"UPDATE job SET {', '.join(sets)} WHERE id = ?", params)
    conn.commit()
    row = get_job(conn, job_id)
    if row is None:
        raise KeyError(job_id)
    return row


# --- Content-hash addressed file storage -------------------------------------

def media_file_path(sha256: str, ext: str, library_dir: Path = LIBRARY_DIR) -> Path:
    return library_dir / f"{sha256}.{ext.lstrip('.')}"


def write_media_file(
    sha256: str, ext: str, data: bytes, library_dir: Path = LIBRARY_DIR
) -> Path:
    ensure_library(library_dir)
    path = media_file_path(sha256, ext, library_dir)
    path.write_bytes(data)
    return path


def read_media_file(sha256: str, ext: str, library_dir: Path = LIBRARY_DIR) -> bytes:
    return media_file_path(sha256, ext, library_dir).read_bytes()


def source_wav_path(sha256: str, library_dir: Path = LIBRARY_DIR) -> Path:
    """Normalized mono 44.1 kHz WAV written by the upload stage for recognition."""
    return library_dir / sha256 / "source.wav"


def chords_path(sha256: str, library_dir: Path = LIBRARY_DIR) -> Path:
    return library_dir / sha256 / "chords.json"


def write_chords(
    sha256: str, data: bytes, library_dir: Path = LIBRARY_DIR
) -> Path:
    ensure_library(library_dir)
    path = chords_path(sha256, library_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def read_chords(sha256: str, library_dir: Path = LIBRARY_DIR) -> bytes:
    return chords_path(sha256, library_dir).read_bytes()
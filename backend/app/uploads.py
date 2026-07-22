"""Multipart upload ingestion: validation, content-hash dedup, ffmpeg normalization.

The upload endpoint (`POST /media`) returns as soon as the file is stored and
normalized. The media row is inserted as `queued`; queueing the recognition job
is wired in the endpoint, which creates a `job` row and hands it to
FastAPI `BackgroundTasks`.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastapi import UploadFile

from app import persistence
from app.persistence import MediaRow, MediaStatus

logger = logging.getLogger(__name__)

# Open decision #1 (design-v1.md) — locked here: 50 MB, {mp3, wav, flac, m4a}.
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_EXTS = frozenset({"mp3", "wav", "flac", "m4a"})

# Must match `frontend/lib/peaks.ts` `PEAKS_PER_SECOND`. A single shared value
# across the two sites keeps bucket→time mapping in sync; do not drift.
PEAKS_PER_SECOND = 1000

_CHUNK = 1024 * 1024


class UploadError(Exception):
    """Validation or processing failure mapped to an HTTP status by the router."""

    def __init__(self, detail: str, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class IngestedMedia:
    row: MediaRow
    created: bool  # False when deduped against an existing sha256 row


def _ext_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _normalize_to_wav(input_path, output_path) -> None:
    """ffmpeg -i <in> -ac 1 -ar 44100 <out>.wav; stderr captured for diagnostics.

    `-y` overwrites output without prompting, so a stale source.wav from a
    prior run is replaced cleanly instead of stalling ffmpeg on a prompt.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_path), "-ac", "1", "-ar", "44100",
         str(output_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")
        logger.error("ffmpeg normalization failed (rc=%s):\n%s", result.returncode, stderr)
        raise UploadError(f"ffmpeg normalization failed: {stderr.strip()}", 500)


def _wav_duration(wav_path) -> float:
    with wave.open(str(wav_path), "rb") as w:
        return w.getnframes() / w.getframerate()


def _compute_peaks(source_wav: Path, peaks_per_second: int = PEAKS_PER_SECOND) -> bytes:
    """Max-abs per-bucket peaks of the normalized WAV as little-endian float32 bytes.

    ffmpeg writes mono pcm_s16le (16 bits), so sampwidth is 2 (2 bytes); the
    assumption is logged rather than handled because any other sample width
    would mean ffmpeg's output contract changed, which is a code change, not
    a runtime branch.
    """
    with wave.open(str(source_wav), "rb") as w:
        nframes = w.getnframes()
        sampwidth = w.getsampwidth()
        framerate = w.getframerate()
        frames = w.readframes(nframes)
    if sampwidth != 2:
        raise UploadError(
            f"unexpected sample width {sampwidth} from ffmpeg (expected 2)", 500
        )
    samples = np.asarray(
        np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0,
        dtype=np.float32,
    )
    bucket_size = max(1, framerate // peaks_per_second)
    n_buckets = samples.size // bucket_size
    trim = n_buckets * bucket_size
    absvals = np.abs(samples[:trim]).reshape(n_buckets, bucket_size)
    return absvals.max(axis=1).tobytes()


async def ingest_upload(
    file: UploadFile,
    *,
    db_path = None,
    library_dir = None,
) -> IngestedMedia:
    """Validate, dedup, store, and normalize an uploaded file.

    DB / library paths default to the module constants in `app.persistence`;
    tests pass tmp paths so the repo's `library/` is never touched.
    """
    db_path = persistence.DB_PATH if db_path is None else db_path
    library_dir = persistence.LIBRARY_DIR if library_dir is None else library_dir

    filename = file.filename or ""
    ext = _ext_of(filename)
    if ext not in ALLOWED_EXTS:
        raise UploadError(f"unsupported format: .{ext or '?'}", 415)

    hasher = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise UploadError(
                f"file exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit", 413
            )
        hasher.update(chunk)
        chunks.append(chunk)
    sha = hasher.hexdigest()
    data = b"".join(chunks)

    conn = persistence.open_db(db_path)
    try:
        existing = persistence.get_media_by_sha256(conn, sha)
        if existing is not None:
            return IngestedMedia(row=existing, created=False)

        persistence.write_media_file(sha, ext, data, library_dir=library_dir)
        source_wav = persistence.source_wav_path(sha, library_dir=library_dir)
        _normalize_to_wav(
            persistence.media_file_path(sha, ext, library_dir=library_dir),
            source_wav,
        )
        duration = _wav_duration(source_wav)
        peaks = _compute_peaks(source_wav)
        persistence.write_peaks(sha, peaks, library_dir=library_dir)
        row = persistence.insert_media(
            conn,
            sha256=sha,
            original_filename=filename,
            duration=duration,
            status=MediaStatus.queued,
        )
        return IngestedMedia(row=row, created=True)
    finally:
        conn.close()
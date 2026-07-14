"""Round-trip checks for the persistence module.

Run: `uv run pytest`. Each test uses pytest's `tmp_path` so the repo's
`library/` is never touched.
"""

from __future__ import annotations

import sqlite3

from app.persistence import (
    MediaStatus,
    get_media,
    init_library,
    insert_media,
    list_media,
    read_chords,
    read_media_file,
    write_chords,
    write_media_file,
)


def test_schema_created_and_restart_is_idempotent(tmp_path):
    db_path = tmp_path / "library" / "index.db"
    library_dir = tmp_path / "library"

    init_library(db_path=db_path, library_dir=library_dir)
    assert db_path.exists()

    # Restarting on an existing DB must not error.
    init_library(db_path=db_path, library_dir=library_dir)


def test_media_round_trip(tmp_path):
    db_path = tmp_path / "library" / "index.db"
    library_dir = tmp_path / "library"
    init_library(db_path=db_path, library_dir=library_dir)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = insert_media(
            conn,
            sha256="a" * 64,
            original_filename="clip.mp3",
            duration=12.5,
        )

        fetched = get_media(conn, row.id)
        assert fetched is not None
        assert fetched.id == row.id
        assert fetched.sha256 == "a" * 64
        assert fetched.original_filename == "clip.mp3"
        assert fetched.duration == 12.5
        assert fetched.status == MediaStatus.queued
        assert fetched.has_chords is False

        rows = list_media(conn)
        assert len(rows) == 1
        assert rows[0].id == row.id

        assert get_media(conn, "media_nope") is None
    finally:
        conn.close()


def test_media_file_and_chords_storage(tmp_path):
    library_dir = tmp_path / "library"
    sha = "b" * 64

    media_path = write_media_file(sha, "mp3", b"audio-bytes", library_dir=library_dir)
    assert media_path == library_dir / f"{sha}.mp3"
    assert read_media_file(sha, "mp3", library_dir=library_dir) == b"audio-bytes"

    chords_path = write_chords(sha, b'{"chords": []}', library_dir=library_dir)
    assert chords_path == library_dir / sha / "chords.json"
    assert read_chords(sha, library_dir=library_dir) == b'{"chords": []}'

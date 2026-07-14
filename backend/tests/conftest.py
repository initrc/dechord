"""Shared pytest fixtures for the backend test suite.

Only fixtures live here; shared fake recognizers and helpers live in
`_fakes.py` (imported explicitly by the tests that need them).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app import persistence
from app.persistence import init_library


@pytest.fixture()
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point persistence at a tmp `library/` dir and initialize the DB.

    Used by tests that touch the DB or the library tree directly. Monkeypatches
    `persistence.LIBRARY_DIR` and `persistence.DB_PATH`; callers that pass
    these on to persistence helpers should reference `persistence.DB_PATH`
    (not a captured copy) so the patched value is seen.
    """
    lib = tmp_path / "library"
    monkeypatch.setattr(persistence, "LIBRARY_DIR", lib)
    monkeypatch.setattr(persistence, "DB_PATH", lib / "index.db")
    init_library(db_path=persistence.DB_PATH, library_dir=lib)
    return lib
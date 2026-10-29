from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from kt_movemacc import ph15_database as db
from ktma_guarded_financial_fixtures import file_guard, writer_database


def _set_test_canonical(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr(db, "CANONICAL_DB_PATHS", (path.resolve(),))


def test_linux_rejects_canonical_write_before_file_creation(monkeypatch):
    canonical = writer_database("linux_canonical")
    _set_test_canonical(monkeypatch, canonical)
    monkeypatch.setattr(db.platform, "system", lambda: "Linux")

    with pytest.raises(db.CanonicalWritePlatformError, match="authorized only from Windows"):
        db.initialize_database(canonical, boundary_guard=file_guard(canonical, with_sqlite_sidecars=True))

    assert not canonical.exists()


def test_windows_allows_canonical_write(monkeypatch):
    canonical = writer_database("windows_canonical")
    _set_test_canonical(monkeypatch, canonical)
    monkeypatch.setattr(db.platform, "system", lambda: "Windows")

    db.initialize_database(canonical, boundary_guard=file_guard(canonical, with_sqlite_sidecars=True))

    assert canonical.exists()


def test_linux_allows_canonical_read_only_access(monkeypatch):
    canonical = writer_database("readonly")
    _set_test_canonical(monkeypatch, canonical)
    monkeypatch.setattr(db.platform, "system", lambda: "Windows")
    db.initialize_database(canonical, boundary_guard=file_guard(canonical, with_sqlite_sidecars=True))
    monkeypatch.setattr(db.platform, "system", lambda: "Linux")

    with db.connect(canonical, read_only=True) as conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("CREATE TABLE blocked(value INTEGER)")


def test_linux_allows_disposable_database_writes(monkeypatch):
    canonical = writer_database("disposable", "canonical.sqlite")
    disposable = writer_database("disposable")
    _set_test_canonical(monkeypatch, canonical)
    monkeypatch.setattr(db.platform, "system", lambda: "Linux")

    db.initialize_database(disposable, boundary_guard=file_guard(disposable, with_sqlite_sidecars=True))

    assert disposable.exists()


def test_linux_rejects_backup_to_canonical_target(monkeypatch):
    source = writer_database("backup_source", "source.sqlite")
    canonical = writer_database("backup_canonical")
    monkeypatch.setattr(db.platform, "system", lambda: "Windows")
    db.initialize_database(source, boundary_guard=file_guard(source, with_sqlite_sidecars=True))
    _set_test_canonical(monkeypatch, canonical)
    monkeypatch.setattr(db.platform, "system", lambda: "Linux")

    with pytest.raises(db.CanonicalWritePlatformError, match="authorized only from Windows"):
        db.backup_database(
            source,
            canonical,
            boundary_guard=file_guard(canonical, with_sqlite_sidecars=True),
        )

    assert not canonical.exists()

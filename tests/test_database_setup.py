import os
import sqlite3
import subprocess
import sys

import pytest

from vm_server.database import SchemaError, connect_database, initialize_database
from vm_server.settings import Settings


def test_database_setup_survives_reopen_and_keeps_existing_data(tmp_path):
    path = tmp_path / "store" / "visionmachine.db"
    assert initialize_database(path) == 1
    with connect_database(path) as db:
        db.execute("""INSERT INTO inspections(
            inspection_id, owner_id, subject_id, subject_type, batch_id, crop_code,
            captured_at_utc, received_at_utc, image_storage_key,
            image_sha256, request_sha256, metadata_json, is_mock
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            "synthetic-id", "synthetic-owner", "synthetic-plant", "plant", "synthetic-batch", "basil",
            "2026-09-19T00:00:00Z", "2026-09-19T00:00:01Z", "synthetic.jpg",
            "a" * 64, "b" * 64, "{}", 1,
        ))
    initialize_database(path)
    with connect_database(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("SELECT inspection_id FROM inspections").fetchone()[0] == "synthetic-id"
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO analyses(analysis_id,inspection_id,status,created_at_utc) "
                       "VALUES('synthetic-analysis','missing','pending_model','synthetic-time')")


def test_unknown_existing_database_is_not_adopted_or_destroyed(tmp_path):
    path = tmp_path / "unknown.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE existing_notes(note TEXT)")
        db.execute("INSERT INTO existing_notes VALUES('keep this synthetic note')")
    with pytest.raises(SchemaError, match="unversioned"):
        initialize_database(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT note FROM existing_notes").fetchone()[0] == "keep this synthetic note"
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='inspections'").fetchone()[0] == 0


@pytest.mark.parametrize("version", [1, 2])
def test_invalid_versioned_database_is_rejected(tmp_path, version):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as db:
        db.execute(f"PRAGMA user_version = {version}")
    with pytest.raises(SchemaError):
        initialize_database(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == version


def test_initialization_rolls_back_partial_ddl(tmp_path, monkeypatch):
    class BrokenMigration:
        def joinpath(self, _):
            return self

        def read_text(self, **_):
            return "CREATE TABLE unfinished(id INTEGER);\nINVALID SQL;\n"

    monkeypatch.setattr("vm_server.database.files", lambda _: BrokenMigration())
    path = tmp_path / "broken.db"
    with pytest.raises(sqlite3.OperationalError):
        initialize_database(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM sqlite_master WHERE name='unfinished'").fetchone()[0] == 0


def test_cli_creates_only_local_empty_storage(tmp_path):
    import json
    store = tmp_path / "local-storage"
    result = subprocess.run(
        [sys.executable, "-m", "vm_server", "init-db"],
        env={**os.environ, "VM_STORAGE_DIR": str(store)},
        capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout)["http_storage_implemented"] is False
    assert (store / "visionmachine.db").is_file()
    assert list((store / "uploads").iterdir()) == []


def test_settings_reject_empty_path_without_creating_storage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("VM_STORAGE_DIR", " ")
    with pytest.raises(ValueError, match="must not be empty"):
        Settings.from_environment()
    assert list(tmp_path.iterdir()) == []

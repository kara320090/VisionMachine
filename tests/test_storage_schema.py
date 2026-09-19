import sqlite3
from pathlib import Path

import pytest

SQL = (Path(__file__).resolve().parents[1] / "server/migrations/001_initial.sql").read_text(encoding="utf-8")


@pytest.fixture
def db():
    connection = sqlite3.connect(":memory:")
    connection.executescript(SQL)
    yield connection
    connection.close()


def test_initial_schema_can_be_applied_again(db):
    db.executescript(SQL)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"inspections", "analyses"} <= tables


def test_analysis_cannot_reference_missing_inspection(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO analyses(analysis_id,inspection_id,status,created_at_utc) VALUES(?,?,?,?)",
                   ("fixture-analysis", "missing", "pending_model", "2026-09-19T00:00:00Z"))


def test_inspection_delete_cascades_to_analysis(db):
    db.execute("""INSERT INTO inspections(
        inspection_id,owner_id,subject_id,subject_type,batch_id,crop_code,
        captured_at_utc,received_at_utc,image_storage_key,image_sha256,request_sha256,metadata_json,is_mock
    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        "fixture-inspection", "fixture-owner", "fixture-plant", "plant", "fixture-batch", "basil",
        "2026-09-19T00:00:00Z", "2026-09-19T00:00:01Z", "fixture/photo.jpg", "a"*64, "b"*64, "{}", 1))
    db.execute("INSERT INTO analyses(analysis_id,inspection_id,status,created_at_utc) VALUES(?,?,?,?)",
               ("fixture-analysis", "fixture-inspection", "pending_model", "2026-09-19T00:00:01Z"))
    db.execute("DELETE FROM inspections WHERE inspection_id=?", ("fixture-inspection",))
    assert db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 0

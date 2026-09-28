"""Synthetic bytes only; these tests never upload a real crop photograph."""

import hashlib
import io
import json
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from vm_server.main import app


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "green").save(output, format="PNG")
    return output.getvalue()


def _jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "green").save(output, format="JPEG")
    return output.getvalue()


def _send(client: TestClient, metadata: dict, contents: bytes, media: str = "image/png"):
    return client.post(
        "/v1/inspections",
        data={"metadata": json.dumps(metadata)},
        files={"photo": ("../../outside.png", contents, media)},
    )


def test_real_file_storage_retry_conflict_and_restart(tmp_path: Path, monkeypatch, inspection):
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    contents = _png()
    inspection["image_sha256"] = hashlib.sha256(contents).hexdigest()
    inspection["image_media_type"] = "image/png"
    first = _send(TestClient(app), inspection, contents)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["analysis"]["status"] == "pending_model"
    assert body["analysis"]["outcome"] is None
    assert body["analysis"]["is_mock_input"] is True
    assert "image_storage_key" not in first.text
    assert "outside.png" not in first.text
    saved_files = list((tmp_path / "uploads").iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].read_bytes() == contents
    assert saved_files[0].name != "outside.png"

    retry = _send(TestClient(app), inspection, contents)
    assert retry.status_code == 200
    assert retry.json() == body
    assert len(list((tmp_path / "uploads").iterdir())) == 1

    changed = dict(inspection, subject_id="a-different-plant")
    conflict = _send(TestClient(app), changed, contents)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "ID_CONFLICT"
    assert len(list((tmp_path / "uploads").iterdir())) == 1

    # A fresh client has no in-memory record; lookup comes from persisted SQLite.
    fetched = TestClient(app).get(f"/v1/inspections/{inspection['inspection_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_upload_rejects_hash_invalid_image_and_mime_without_storing(tmp_path, monkeypatch, inspection):
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    contents = _png()
    inspection["image_media_type"] = "image/png"
    inspection["image_sha256"] = "a" * 64
    assert _send(TestClient(app), inspection, contents).json()["detail"]["code"] == "HASH_MISMATCH"

    bad = b"not an image"
    inspection["image_sha256"] = hashlib.sha256(bad).hexdigest()
    assert _send(TestClient(app), inspection, bad).json()["detail"]["code"] == "INVALID_IMAGE"

    inspection["image_sha256"] = hashlib.sha256(contents).hexdigest()
    assert _send(TestClient(app), inspection, contents, "image/jpeg").json()["detail"]["code"] == "INVALID_IMAGE"
    assert not (tmp_path / "uploads").exists()


def test_metadata_validation_size_limit_and_missing_lookup(tmp_path, monkeypatch, inspection):
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    contents = _png()
    inspection["image_sha256"] = hashlib.sha256(contents).hexdigest()
    inspection["image_media_type"] = "image/png"
    inspection["sensor_packet"]["request_id"] = "22222222-2222-4222-8222-222222222222"
    assert _send(TestClient(app), inspection, contents).json()["detail"]["code"] == "INVALID_METADATA"
    inspection["sensor_packet"]["request_id"] = inspection["inspection_id"]
    assert _send(TestClient(app), inspection, contents + b"0" * (12 * 1024 * 1024)).status_code == 413
    missing = TestClient(app).get(f"/v1/inspections/{inspection['inspection_id']}")
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "NOT_FOUND"


def test_local_only_rejects_remote_client(tmp_path, monkeypatch, inspection):
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    remote = TestClient(app, client=("203.0.113.2", 12345))
    result = remote.get(f"/v1/inspections/{inspection['inspection_id']}")
    assert result.status_code == 403
    assert result.json()["detail"]["code"] == "LOCAL_ONLY"


def test_jpeg_upload_and_failed_file_move_leave_no_record(tmp_path, monkeypatch, inspection):
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    contents = _jpeg()
    inspection["image_sha256"] = hashlib.sha256(contents).hexdigest()
    inspection["image_media_type"] = "image/jpeg"
    import vm_server.inspections as storage

    with monkeypatch.context() as patch:
        patch.setattr(storage.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("synthetic failure")))
        failure = _send(TestClient(app), inspection, contents, "image/jpeg")
    assert failure.status_code == 503
    assert failure.json()["detail"]["code"] == "STORAGE_UNAVAILABLE"
    assert list((tmp_path / "uploads").iterdir()) == []
    assert TestClient(app).get(f"/v1/inspections/{inspection['inspection_id']}").status_code == 404

    success = _send(TestClient(app), inspection, contents, "image/jpeg")
    assert success.status_code == 201
    assert len(list((tmp_path / "uploads").glob("*.jpg"))) == 1

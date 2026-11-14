"""Synthetic registration, expiry, quotas and owner isolation; no GPU substitute in production."""
import hashlib
import io
import json
import secrets
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from vm_server.main import app
from vm_server import devices, rgb_inspections


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("VM_API_KEY", "synthetic-administrator-test-key")
    monkeypatch.setenv("VM_DEVICE_ENROLLMENT_ENABLED", "1")
    class ProtocolStub:
        providers = ["CUDAExecutionProvider"]
        def infer(self, raw):
            return {"normal": .25, "abnormal": .75, "model_version": "synthetic-device-protocol-only",
                    "model_sha256": "0" * 64, "elapsed_ms": 0}
    monkeypatch.setattr(rgb_inspections, "engine", ProtocolStub())
    return TestClient(app)


def enrollment():
    return {"schema_version": "0.1.0", "installation_id": str(uuid4()),
            "registration_secret": secrets.token_hex(32), "app_version_code": 6}


def register(client, payload=None):
    payload = payload or enrollment()
    response = client.post("/api/v1/devices/register", json=payload)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return payload, response.json()["api_key"]


def photo():
    image = io.BytesIO()
    Image.new("RGB", (17, 23), "green").save(image, "PNG")
    raw = image.getvalue()
    payload = {"client_inspection_id": str(uuid4()), "photos": [{"source_photo_id": str(uuid4()),
        "crop_code": "basil", "image_sha256": hashlib.sha256(raw).hexdigest(), "image_media_type": "image/png"}]}
    return payload, [("photos", ("synthetic-device.png", raw, "image/png"))]


def test_enrollment_is_explicit_and_bounded(client, monkeypatch):
    monkeypatch.setenv("VM_DEVICE_ENROLLMENT_ENABLED", "0")
    assert client.post("/api/v1/devices/register", json=enrollment()).status_code == 404
    monkeypatch.setenv("VM_DEVICE_ENROLLMENT_ENABLED", "1")
    assert client.post("/api/v1/devices/register", content="x" * 4097).status_code == 413
    monkeypatch.setenv("VM_DEVICE_LIMIT", "1")
    register(client)
    assert client.post("/api/v1/devices/register", json=enrollment()).json()["detail"]["code"] == "DEVICE_LIMIT_REACHED"


def test_recovery_requires_installation_secret_and_registry_has_no_plaintext_tokens(client, tmp_path):
    payload, token = register(client)
    assert register(client, payload)[1] == token
    wrong = dict(payload, registration_secret=secrets.token_hex(32))
    assert client.post("/api/v1/devices/register", json=wrong).status_code == 409
    stored = (tmp_path / "rgb_devices.sqlite3").read_bytes()
    assert token.encode() not in stored and payload["registration_secret"].encode() not in stored
    assert devices.authenticate(token).device_id == payload["installation_id"]


def test_expiry_rotates_token_and_revocation_cannot_register_again(client):
    payload, old_token = register(client)
    with devices.connect() as db:
        db.execute("UPDATE devices SET expires_at=0 WHERE id=?", (payload["installation_id"],))
    assert devices.authenticate(old_token) is None
    new_token = register(client, payload)[1]
    assert old_token != new_token
    assert devices.authenticate(old_token) is None
    with devices.connect() as db:
        db.execute("UPDATE devices SET revoked=1 WHERE id=?", (payload["installation_id"],))
    assert devices.authenticate(new_token) is None
    assert client.post("/api/v1/devices/register", json=payload).status_code == 403


def test_device_cannot_read_or_retry_another_installations_inspection(client):
    _, first = register(client)
    _, second = register(client)
    payload, files = photo()
    send = lambda key: client.post("/api/v1/inspections", headers={"X-API-Key": key},
                                  data={"payload": json.dumps(payload)}, files=files)
    assert send(first).status_code == 201
    assert send(first).status_code == 200
    identity = payload["client_inspection_id"]
    assert client.get(f"/api/v1/inspections/{identity}", headers={"X-API-Key": first}).status_code == 200
    assert client.get(f"/api/v1/inspections/{identity}", headers={"X-API-Key": second}).status_code == 404
    assert send(second).status_code == 404
    assert client.get(f"/api/v1/inspections/{identity}", headers={"X-API-Key": "synthetic-administrator-test-key"}).status_code == 200
    payload, files = photo()
    assert send("synthetic-administrator-test-key").status_code == 201
    assert send(first).status_code == 404


def test_expired_keys_and_unknown_keys_stay_unauthorized(client):
    payload, token = register(client)
    with devices.connect() as db:
        db.execute("UPDATE devices SET expires_at=0 WHERE id=?", (payload["installation_id"],))
    for key in (token, "vm_device_unknown", "", "invalid"):
        assert client.get(f"/api/v1/inspections/{uuid4()}", headers={"X-API-Key": key}).status_code == 401


def test_public_installation_key_does_not_grant_legacy_development_api_access(client):
    _, token = register(client)
    assert client.get("/v1/capabilities").status_code == 401
    assert client.get("/v1/capabilities", headers={"X-API-Key": token}).status_code == 401
    assert client.get("/v1/capabilities", headers={"X-API-Key": "synthetic-administrator-test-key"}).status_code == 200


def test_enrollment_failures_and_authenticated_requests_are_rate_limited(client, monkeypatch):
    fixed_time = 1_800_000_000
    monkeypatch.setattr(devices, "time", SimpleNamespace(time=lambda: fixed_time))
    payload, token = register(client)
    wrong = dict(payload, registration_secret=secrets.token_hex(32))
    for _ in range(29):
        assert client.post("/api/v1/devices/register", json=wrong).status_code == 409
    assert client.post("/api/v1/devices/register", json=wrong).status_code == 429
    bucket = fixed_time // 3600
    with devices.connect() as db:
        db.execute("INSERT INTO usage VALUES (?,?,120)", (payload["installation_id"], bucket))
    response = client.get(f"/api/v1/inspections/{uuid4()}", headers={"X-API-Key": token})
    assert response.status_code == 429 and int(response.headers["retry-after"]) > 0

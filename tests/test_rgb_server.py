"""Synthetic transport tests and Android pixel goldens; no replacement ONNX model."""
import hashlib
import io
import json
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageOps

from vm_server.main import app
from vm_server import rgb_inspections as service
from vm_server.rgb_engine import crop_rgb, preprocess

@pytest.fixture
def sensor_packet(inspection):
    return inspection["sensor_packet"]


def request_data(count=1):
    buffer = io.BytesIO()
    Image.new("RGB", (17, 23), "green").save(buffer, "PNG")
    raw = buffer.getvalue()
    payload = {"client_inspection_id": str(uuid4()), "photos": [
        {"source_photo_id": str(uuid4()), "crop_code": "tomato",
         "image_sha256": hashlib.sha256(raw).hexdigest(), "image_media_type": "image/png"} for _ in range(count)]}
    return payload, [("photos", ("synthetic.png", raw, "image/png")) for _ in range(count)]


def test_missing_model_auth_limits_and_sensor_pairing(tmp_path, monkeypatch, sensor_packet):
    monkeypatch.setenv("VM_API_KEY", "synthetic-test-key-only")
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(service, "engine", None)
    client = TestClient(app)
    payload, files = request_data()
    def send():
        return client.post("/api/v1/inspections", data={"payload": json.dumps(payload)}, files=files,
                           headers={"X-API-Key": "synthetic-test-key-only"})
    assert client.post("/api/v1/inspections", files=files).status_code == 401
    assert send().json()["detail"]["code"] == "MODEL_NOT_READY"
    payload, files = request_data(8)
    assert send().status_code == 503
    payload, files = request_data(9)
    assert send().status_code == 422
    payload, files = request_data()
    photo = payload["photos"][0]
    photo["sensor"] = {"sensor_record_id": sensor_packet["request_id"], "source_photo_id": str(uuid4()),
        "crop_code": "tomato", "photo_sha256": photo["image_sha256"], "received_at": "2026-11-14T00:00:00Z", "packet": sensor_packet}
    assert send().status_code == 422


def test_persistent_idempotency_conflict_and_sensor_snapshot(tmp_path, monkeypatch, sensor_packet):
    class TransportStub:
        """Protocol-only test double, never installed as a server model."""
        providers = ["CUDAExecutionProvider"]
        calls = 0
        def infer(self, raw):
            self.calls += 1
            return {"normal": .25, "abnormal": .75, "model_version": "synthetic-protocol-stub",
                    "model_sha256": "0" * 64, "elapsed_ms": 0}
    stub = TransportStub()
    monkeypatch.setattr(service, "engine", stub)
    monkeypatch.setenv("VM_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("VM_API_KEY", "synthetic-test-key-only")
    client = TestClient(app)
    payload, files = request_data(8)
    p = payload["photos"][0]
    assessment = json.dumps({"profile": {"crop": "tomato"}, "deviation_score": None})
    p["sensor"] = {"sensor_record_id": sensor_packet["request_id"], "source_photo_id": p["source_photo_id"],
        "crop_code": "tomato", "photo_sha256": p["image_sha256"], "received_at": "2026-11-14T00:00:00Z",
        "packet": sensor_packet, "assessment_json": assessment}
    def send():
        return client.post("/api/v1/inspections", data={"payload": json.dumps(payload)}, files=files,
                           headers={"X-API-Key": "synthetic-test-key-only"})
    first = send()
    assert first.status_code == 201, first.text
    assert len(first.json()["photos"]) == 8
    assert first.json()["photos"][0]["sensor"]["assessment_json"] == assessment
    assert send().json() == first.json()
    assert stub.calls == 8
    monkeypatch.setattr(service, "engine", None)
    assert send().status_code == 200  # persisted response survives unavailable model
    p["crop_code"] = "pepper"
    p["sensor"] = None
    assert send().status_code == 409


@pytest.mark.parametrize("w,h,expected", [
    (71,53,"c38cc40c1f2dffa6e14291de4f98f8265e9823bbf297f8184987b6c171bbc9bc"),
    (53,71,"0f154700878a80a927b8a555be822967024a48d88231fb8b646c638f3c9ad819"),
    (256,256,"7cfacf8b6b0eb0cb8798654284fa94551335f5fad5de817e6514b0159a1e9f13"),
    (1001,601,"4e50448eec58bba4321e4a013caa2091160ee7217d88620b9bcf2d441eed74b1"),
    (3000,4000,"fd4589c8787702fb5c8e013bfc323a87d2a6659554656d4917b37d58be147405")])
def test_pillow_matches_existing_android_pixel_goldens(w, h, expected):
    x = np.arange(w)[None, :]
    y = np.arange(h)[:, None]
    image = Image.fromarray(np.stack([(x*13+y*7)%256, (x*3+y*19)%256, (x*29+y*5)%256], axis=-1).astype("uint8"))
    assert hashlib.sha256(crop_rgb(image).tobytes()).hexdigest() == expected
    tensor = preprocess(image)
    assert tensor.shape == (1, 3, 224, 224) and tensor.dtype == np.float32
    for orientation in range(1, 9):
        oriented = image.copy()
        oriented.getexif()[274] = orientation
        assert np.array_equal(preprocess(oriented), preprocess(ImageOps.exif_transpose(oriented)))

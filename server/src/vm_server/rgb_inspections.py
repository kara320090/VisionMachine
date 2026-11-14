"""Authenticated RGB upload, original sensor snapshots, persistent idempotent replies."""
import hashlib
import hmac
import io
import json
import os
import sqlite3
import threading
import warnings
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import ValidationError

from vm_contracts.models import RgbInspectionRequest, RgbInspectionResult
from vm_server.rgb_engine import RgbEngine
from vm_server.settings import Settings

router = APIRouter()
engine = None
model_error = "MODEL_NOT_LOADED"
lock = threading.Lock()
MAX_IMAGE_BYTES = 24 * 1024 * 1024


def load_engine():
    global engine, model_error
    try:
        engine = RgbEngine()
        model_error = None
    except Exception as error:
        engine = None
        model_error = str(error)


def authorized(value):
    key = os.environ.get("VM_API_KEY", "")
    return bool(key and value and hmac.compare_digest(value.encode(), key.encode()))


def failure(status, code):
    return HTTPException(status_code=status, detail={"code": code})


def connect():
    folder = Settings.from_environment().storage_dir
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder / "rgb_inspections.sqlite3", timeout=30)
    db.execute("CREATE TABLE IF NOT EXISTS rgb_inspections (id TEXT PRIMARY KEY, request_sha TEXT NOT NULL, result TEXT NOT NULL)")
    return db


@router.get("/health/live")
def live():
    return {"status": "alive"}


@router.get("/health/ready")
def ready():
    if engine is None:
        return JSONResponse(status_code=503, content={"status": "not_ready", "reason": model_error})
    return {"status": "ready", "providers": engine.providers, "model": engine.card,
            "input": {"name": "image", "shape": [1, 3, 224, 224], "type": "tensor(float)"}}


def validate_image(raw, media):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                w, h = image.size
                if image.format != {"image/jpeg": "JPEG", "image/png": "PNG"}[media] or w * h > 24_000_000 or max(w, h) > 16384 or max(w, h) / min(w, h) > 40:
                    raise ValueError("image bounds or format")
                image.verify()
    except (OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise failure(422, "INVALID_IMAGE") from None


def process(payload, blobs):
    # One worker and lock serialize GPU work and duplicate submission commits.
    canonical = payload.model_dump_json()
    request_sha = hashlib.sha256(canonical.encode()).hexdigest()
    identity = str(payload.client_inspection_id)
    with lock, connect() as db:
        prior = db.execute("SELECT request_sha, result FROM rgb_inspections WHERE id=?", (identity,)).fetchone()
        if prior:
            if prior[0] != request_sha:
                raise failure(409, "ID_CONFLICT")
            return 200, json.loads(prior[1])
        if engine is None:
            raise failure(503, "MODEL_NOT_READY")
        results = []
        for index, (photo, raw) in enumerate(zip(payload.photos, blobs), 1):
            row = {"index": index, "source_photo_id": str(photo.source_photo_id),
                   "crop_code": photo.crop_code, "image_sha256": photo.image_sha256,
                   "sensor": photo.sensor.model_dump(mode="json") if photo.sensor else None}
            if photo.crop_code == "eggplant":
                row.update(status="failed", error_code="CROP_OUT_OF_SCOPE")
            else:
                try:
                    row.update(engine.infer(raw), status="completed", error_code=None)
                except Exception:
                    # Do not cache transient GPU failures as a permanent retry result.
                    raise failure(503, "INFERENCE_FAILED") from None
            results.append(row)
        result = {"schema_version": "0.1.0", "inspection_id": identity,
                  "client_inspection_id": identity, "created_at": datetime.now(timezone.utc).isoformat(),
                  "providers": engine.providers, "photos": results,
                  "sensor_scoring": "app_snapshot_only"}
        result = RgbInspectionResult.model_validate(result).model_dump(mode="json")
        # Original bytes retain EXIF and content hashes; never re-encode for storage.
        folder = Settings.from_environment().storage_dir / "rgb_uploads" / (identity + "-" + uuid4().hex)
        folder.mkdir(parents=True, exist_ok=False)
        try:
            for photo, raw in zip(payload.photos, blobs):
                (folder / f"{photo.source_photo_id}.bin").write_bytes(raw)
            (folder / "payload.json").write_text(canonical, encoding="utf-8")
            db.execute("INSERT INTO rgb_inspections VALUES (?,?,?)", (identity, request_sha, json.dumps(result, allow_nan=False)))
            db.commit()
        except BaseException:
            for item in folder.iterdir():
                item.unlink()
            folder.rmdir()
            raise
        return 201, result


@router.post("/api/v1/inspections", response_model=RgbInspectionResult)
async def upload(photos: list[UploadFile] = File(...), payload: str = Form(...)):
    try:
        if len(payload.encode()) > 64 * 1024:
            raise failure(413, "METADATA_TOO_LARGE")
        try:
            parsed = RgbInspectionRequest.model_validate_json(payload)
        except ValidationError:
            raise failure(422, "INVALID_METADATA") from None
        if not 1 <= len(photos) <= 8 or len(photos) != len(parsed.photos):
            raise failure(422, "PHOTO_COUNT_MISMATCH")
        blobs = []
        for upload_file, photo in zip(photos, parsed.photos):
            raw = await upload_file.read(MAX_IMAGE_BYTES + 1)
            if len(raw) > MAX_IMAGE_BYTES:
                raise failure(413, "IMAGE_TOO_LARGE")
            if upload_file.content_type != photo.image_media_type:
                raise failure(422, "INVALID_IMAGE")
            if hashlib.sha256(raw).hexdigest() != photo.image_sha256:
                raise failure(422, "HASH_MISMATCH")
            await run_in_threadpool(validate_image, raw, photo.image_media_type)
            blobs.append(raw)
        status, result = await run_in_threadpool(process, parsed, blobs)
        return JSONResponse(status_code=status, content=result)
    finally:
        for photo in photos:
            await photo.close()


@router.get("/api/v1/inspections/{inspection_id}", response_model=RgbInspectionResult)
def lookup(inspection_id: UUID):
    with connect() as db:
        row = db.execute("SELECT result FROM rgb_inspections WHERE id=?", (str(inspection_id),)).fetchone()
    if row is None:
        raise failure(404, "NOT_FOUND")
    return json.loads(row[0])

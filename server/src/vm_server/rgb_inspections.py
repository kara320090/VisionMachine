"""Authenticated RGB upload, original sensor snapshots, persistent idempotent replies."""
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import threading
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Request
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
    db.execute("CREATE TABLE IF NOT EXISTS rgb_owners (inspection_id TEXT PRIMARY KEY, device_id TEXT NOT NULL)")
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


def validate_upload(upload, photo):
    source = upload.file
    if source.seek(0, os.SEEK_END) > MAX_IMAGE_BYTES:
        raise failure(413, "IMAGE_TOO_LARGE")
    if upload.content_type != photo.image_media_type:
        raise failure(422, "INVALID_IMAGE")
    source.seek(0)
    if hashlib.file_digest(source, "sha256").hexdigest() != photo.image_sha256:
        raise failure(422, "HASH_MISMATCH")
    source.seek(0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as image:
                w, h = image.size
                if image.format != {"image/jpeg": "JPEG", "image/png": "PNG"}[photo.image_media_type] or w * h > 24_000_000 or max(w, h) > 16384 or max(w, h) / min(w, h) > 40:
                    raise ValueError("image bounds or format")
                image.verify()
    except (OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise failure(422, "INVALID_IMAGE") from None
    source.seek(0)


@contextmanager
def processing_lock_wait_ms():
    queued_at = perf_counter_ns()
    with lock:
        yield (perf_counter_ns() - queued_at) / 1_000_000


def process(payload, uploads, owner_id=None):
    # The multipart parser owns each seekable spool until the response is ready.
    for upload, photo in zip(uploads, payload.photos):
        validate_upload(upload, photo)
    # One worker and lock serialize GPU work and duplicate submission commits.
    canonical = payload.model_dump_json()
    request_sha = hashlib.sha256(canonical.encode()).hexdigest()
    identity = str(payload.client_inspection_id)
    with processing_lock_wait_ms() as queue_ms, connect() as db:
        prior = db.execute("SELECT request_sha, result FROM rgb_inspections WHERE id=?", (identity,)).fetchone()
        if prior:
            owner = db.execute("SELECT device_id FROM rgb_owners WHERE inspection_id=?", (identity,)).fetchone()
            if owner_id is not None and (owner is None or owner[0] != owner_id):
                raise failure(404, "NOT_FOUND")
            if prior[0] != request_sha:
                raise failure(409, "ID_CONFLICT")
            return 200, json.loads(prior[1]), queue_ms
        if engine is None:
            raise failure(503, "MODEL_NOT_READY")
        results = []
        for index, (photo, upload) in enumerate(zip(payload.photos, uploads), 1):
            row = {"index": index, "source_photo_id": str(photo.source_photo_id),
                   "crop_code": photo.crop_code, "image_sha256": photo.image_sha256,
                   "sensor": photo.sensor.model_dump(mode="json") if photo.sensor else None}
            if photo.crop_code == "eggplant":
                row.update(status="failed", error_code="CROP_OUT_OF_SCOPE")
            else:
                try:
                    row.update(engine.infer(upload.file), status="completed", error_code=None)
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
            for photo, upload in zip(payload.photos, uploads):
                upload.file.seek(0)
                with (folder / f"{photo.source_photo_id}.bin").open("wb") as target:
                    shutil.copyfileobj(upload.file, target, length=256 * 1024)
            (folder / "payload.json").write_text(canonical, encoding="utf-8")
            db.execute("INSERT INTO rgb_inspections VALUES (?,?,?)", (identity, request_sha, json.dumps(result, allow_nan=False)))
            if owner_id is not None:
                db.execute("INSERT INTO rgb_owners VALUES (?,?)", (identity, owner_id))
            db.commit()
        except BaseException:
            for item in folder.iterdir():
                item.unlink()
            folder.rmdir()
            raise
        return 201, result, queue_ms


@router.post("/api/v1/inspections", response_model=RgbInspectionResult)
async def upload(request: Request, photos: list[UploadFile] = File(...), payload: str = Form(...)):
    try:
        if len(payload.encode()) > 64 * 1024:
            raise failure(413, "METADATA_TOO_LARGE")
        try:
            parsed = RgbInspectionRequest.model_validate_json(payload)
        except ValidationError:
            raise failure(422, "INVALID_METADATA") from None
        if not 1 <= len(photos) <= 8 or len(photos) != len(parsed.photos):
            raise failure(422, "PHOTO_COUNT_MISMATCH")
        status, result, queue_ms = await run_in_threadpool(process, parsed, photos, request.state.rgb_owner)
        timing = f"vm_queue;dur={queue_ms:.3f}"
        if status == 201:
            inference_times = [row["elapsed_ms"] for row in result["photos"] if row["status"] == "completed"]
            if inference_times:
                timing += f", vm_infer;dur={sum(inference_times)}"
        return JSONResponse(status_code=status, content=result, headers={"Server-Timing": timing})
    finally:
        for photo in photos:
            await photo.close()


@router.get("/api/v1/inspections/{inspection_id}", response_model=RgbInspectionResult)
def lookup(inspection_id: UUID, request: Request):
    with connect() as db:
        row = db.execute("SELECT result FROM rgb_inspections WHERE id=?", (str(inspection_id),)).fetchone()
        owner = db.execute("SELECT device_id FROM rgb_owners WHERE inspection_id=?", (str(inspection_id),)).fetchone()
        if request.state.rgb_owner is not None and (owner is None or owner[0] != request.state.rgb_owner):
            raise failure(404, "NOT_FOUND")
    if row is None:
        raise failure(404, "NOT_FOUND")
    return json.loads(row[0])

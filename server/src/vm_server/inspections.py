"""Local development photo storage. This is not an authenticated public API."""

import hashlib
import io
import json
import os
import sqlite3
import warnings
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ValidationError

from vm_contracts.models import AnalysisResult, InspectionMetadata
from vm_ml.interface import pending_result
from vm_server.database import SchemaError, connect_database, initialize_database
from vm_server.settings import Settings

router = APIRouter(prefix="/v1/inspections", tags=["local inspections"])
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
MAX_METADATA_BYTES = 64 * 1024
LOCAL_OWNER = "local-development-only"


class StoredInspection(BaseModel):
    inspection_id: UUID
    metadata: InspectionMetadata
    analysis: AnalysisResult
    received_at_utc: datetime


def _error(status: int, code: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "request_id": str(uuid4())})


def _local_only(request: Request) -> None:
    if request.client is None or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise _error(403, "LOCAL_ONLY")


def _settings() -> Settings:
    try:
        settings = Settings.from_environment()
        initialize_database(settings.database_path)
        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        return settings
    except (ValueError, OSError, sqlite3.Error, SchemaError):
        raise _error(503, "STORAGE_UNAVAILABLE") from None


def _validate_image(contents: bytes, media_type: str) -> str:
    expected = {"image/jpeg": ("JPEG", ".jpg"), "image/png": ("PNG", ".png")}
    if media_type not in expected or not contents:
        raise _error(422, "INVALID_IMAGE")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as image:
                if image.format != expected[media_type][0] or image.width * image.height > MAX_IMAGE_PIXELS:
                    raise _error(422, "INVALID_IMAGE")
                image.verify()
            with Image.open(io.BytesIO(contents)) as image:
                image.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise _error(422, "INVALID_IMAGE") from None
    return expected[media_type][1]


def _stored(row: sqlite3.Row) -> StoredInspection:
    return StoredInspection(
        inspection_id=row["inspection_id"],
        metadata=InspectionMetadata.model_validate_json(row["metadata_json"]),
        analysis=AnalysisResult.model_validate_json(row["result_json"]),
        received_at_utc=row["received_at_utc"],
    )


def _load(settings: Settings, inspection_id: UUID) -> StoredInspection | None:
    with connect_database(settings.database_path) as connection:
        row = connection.execute(
            """SELECT i.inspection_id, i.metadata_json, i.received_at_utc, a.result_json
               FROM inspections i JOIN analyses a ON a.inspection_id=i.inspection_id
               WHERE i.inspection_id=? AND i.owner_id=? AND i.deleted_at_utc IS NULL
               ORDER BY a.created_at_utc DESC LIMIT 1""",
            (str(inspection_id), LOCAL_OWNER),
        ).fetchone()
    return _stored(row) if row is not None else None


def _persist(settings: Settings, metadata: InspectionMetadata, contents: bytes, extension: str) -> tuple[int, StoredInspection]:
    canonical = json.dumps(metadata.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    request_sha = hashlib.sha256(canonical.encode("utf-8") + b"\0" + bytes.fromhex(metadata.image_sha256)).hexdigest()
    received_at = datetime.now(timezone.utc).isoformat()
    analysis = pending_result(metadata)
    key = uuid4().hex + extension
    destination = settings.uploads_dir / key
    temporary = settings.uploads_dir / (".incoming-" + uuid4().hex)
    moved = False
    committed = False
    try:
        with temporary.open("xb") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        with connect_database(settings.database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                existing = connection.execute(
                    "SELECT request_sha256 FROM inspections WHERE inspection_id=? AND owner_id=?",
                    (str(metadata.inspection_id), LOCAL_OWNER),
                ).fetchone()
                if existing is not None:
                    connection.rollback()
                    if existing["request_sha256"] != request_sha:
                        raise _error(409, "ID_CONFLICT")
                    stored = _load(settings, metadata.inspection_id)
                    if stored is None:
                        raise _error(503, "STORAGE_UNAVAILABLE")
                    return 200, stored
                os.replace(temporary, destination)
                moved = True
                connection.execute(
                    """INSERT INTO inspections (
                       inspection_id, owner_id, subject_id, subject_type, parent_plant_id,
                       batch_id, crop_code, captured_at_utc, received_at_utc,
                       image_storage_key, image_sha256, request_sha256, metadata_json, is_mock)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (str(metadata.inspection_id), LOCAL_OWNER, metadata.subject_id, metadata.subject_type,
                     metadata.parent_plant_id, metadata.batch_id, metadata.crop_code,
                     metadata.captured_at.astimezone(timezone.utc).isoformat(), received_at,
                     key, metadata.image_sha256, request_sha, canonical, int(metadata.is_mock)),
                )
                connection.execute(
                    """INSERT INTO analyses(analysis_id, inspection_id, status, result_json, created_at_utc)
                       VALUES(?,?,?,?,?)""",
                    (str(uuid4()), str(metadata.inspection_id), analysis.status,
                     analysis.model_dump_json(), received_at),
                )
                connection.commit()
                committed = True
            except BaseException:
                connection.rollback()
                raise
    except HTTPException:
        raise
    except (OSError, sqlite3.Error):
        raise _error(503, "STORAGE_UNAVAILABLE") from None
    finally:
        temporary.unlink(missing_ok=True)
        if moved and not committed:
            destination.unlink(missing_ok=True)
    return 201, StoredInspection(
        inspection_id=metadata.inspection_id, metadata=metadata,
        analysis=analysis, received_at_utc=received_at,
    )


@router.post("", response_model=StoredInspection, status_code=201)
async def upload_inspection(
    request: Request, response: Response,
    photo: UploadFile = File(...), metadata: str = Form(...),
) -> StoredInspection:
    _local_only(request)
    if len(metadata.encode("utf-8")) > MAX_METADATA_BYTES:
        raise _error(413, "METADATA_TOO_LARGE")
    try:
        parsed = InspectionMetadata.model_validate_json(metadata)
    except ValidationError:
        raise _error(422, "INVALID_METADATA") from None
    contents = await photo.read(MAX_IMAGE_BYTES + 1)
    await photo.close()
    if len(contents) > MAX_IMAGE_BYTES:
        raise _error(413, "IMAGE_TOO_LARGE")
    image_sha = hashlib.sha256(contents).hexdigest()
    if image_sha != parsed.image_sha256:
        raise _error(422, "HASH_MISMATCH")
    extension = _validate_image(contents, parsed.image_media_type)
    if photo.content_type != parsed.image_media_type:
        raise _error(422, "INVALID_IMAGE")
    status, stored = _persist(_settings(), parsed, contents, extension)
    response.status_code = status
    return stored


@router.get("/{inspection_id}", response_model=StoredInspection)
def get_inspection(request: Request, inspection_id: UUID) -> StoredInspection:
    _local_only(request)
    try:
        stored = _load(_settings(), inspection_id)
    except (OSError, sqlite3.Error, ValidationError):
        raise _error(503, "STORAGE_UNAVAILABLE") from None
    if stored is None:
        raise _error(404, "NOT_FOUND")
    return stored

"""Local development server. Storage is real; diagnosis is pending."""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from vm_contracts.models import AnalysisResult, InspectionMetadata, CROP_CODES, VERSION
from vm_ml.interface import pending_result
from vm_server.inspections import router as inspections_router
from vm_server import rgb_inspections, devices

@asynccontextmanager
async def lifespan(app):
    rgb_inspections.load_engine()
    yield

app = FastAPI(title="VisionMachine Foundation", version=VERSION, lifespan=lifespan,
              description="Local storage and authenticated CUDA RGB inspections; sensor scoring remains in Android.")
app.include_router(inspections_router)
app.include_router(rgb_inspections.router)
app.include_router(devices.router)

@app.middleware("http")
async def rgb_authentication(request: Request, call_next):
    # Automatic public installs must not inherit access to the old development API.
    if os.environ.get("VM_DEVICE_ENROLLMENT_ENABLED") == "1" and request.url.path.startswith("/v1/"):
        if not rgb_inspections.authorized(request.headers.get("X-API-Key")):
            return JSONResponse(status_code=401, content={"detail": {"code": "UNAUTHORIZED"}})
    if request.url.path.startswith("/api/"):
        enrollment = request.url.path == "/api/v1/devices/register" and request.method == "POST"
        if not enrollment:
            principal = await run_in_threadpool(devices.authenticate, request.headers.get("X-API-Key"))
            if principal is None:
                return JSONResponse(status_code=401, content={"detail": {"code": "UNAUTHORIZED"}})
            try:
                await run_in_threadpool(devices.consume_request, principal)
            except HTTPException as error:
                return JSONResponse(status_code=error.status_code, content={"detail": error.detail}, headers=error.headers)
            request.state.rgb_owner = principal.device_id
        try:
            length = int(request.headers.get("Content-Length", "0"))
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": {"code": "INVALID_CONTENT_LENGTH"}})
        if enrollment and length == 0:
            return JSONResponse(status_code=411, content={"detail": {"code": "CONTENT_LENGTH_REQUIRED"}})
        maximum = 4096 if enrollment else 8 * rgb_inspections.MAX_IMAGE_BYTES + 128 * 1024
        if length < 0 or length > maximum:
            return JSONResponse(status_code=413, content={"detail": {"code": "REQUEST_TOO_LARGE"}})
    return await call_next(request)

@app.get("/healthz")
def health():
    return {"status": "ok", "stage": "storage_and_rgb", "model_available": rgb_inspections.engine is not None}

@app.get("/v1/capabilities")
def capabilities():
    return {"schema_version": VERSION, "crop_catalog": CROP_CODES,
            "validated_diagnostic_crops": [], "model_available": rgb_inspections.engine is not None,
            "implemented": ["metadata_validation", "local_image_upload", "local_storage", "local_inspection_lookup",
                            "authenticated_rgb_upload", "rgb_idempotent_lookup"],
            "pending": ["user_authentication", "field_validation", "history", "delete"]}

@app.post("/v1/dev/validate-inspection", response_model=AnalysisResult)
def validate_inspection(metadata: InspectionMetadata):
    # Validates structure only. There are no photo bytes here to verify or store.
    return pending_result(metadata)

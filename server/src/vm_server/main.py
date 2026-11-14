"""Local development server. Storage is real; diagnosis is pending."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from vm_contracts.models import AnalysisResult, InspectionMetadata, CROP_CODES, VERSION
from vm_ml.interface import pending_result
from vm_server.inspections import router as inspections_router
from vm_server import rgb_inspections

@asynccontextmanager
async def lifespan(app):
    rgb_inspections.load_engine()
    yield

app = FastAPI(title="VisionMachine Foundation", version=VERSION, lifespan=lifespan,
              description="Local storage and authenticated CUDA RGB inspections; sensor scoring remains in Android.")
app.include_router(inspections_router)
app.include_router(rgb_inspections.router)

@app.middleware("http")
async def rgb_authentication(request: Request, call_next):
    if request.url.path.startswith("/api/") and not rgb_inspections.authorized(request.headers.get("X-API-Key")):
        return JSONResponse(status_code=401, content={"detail": {"code": "UNAUTHORIZED"}})
    if request.url.path.startswith("/api/"):
        try:
            length = int(request.headers.get("Content-Length", "0"))
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": {"code": "INVALID_CONTENT_LENGTH"}})
        if length < 0 or length > 8 * rgb_inspections.MAX_IMAGE_BYTES + 128 * 1024:
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

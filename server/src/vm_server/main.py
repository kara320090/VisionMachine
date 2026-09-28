"""Local development server. Storage is real; diagnosis is pending."""
from fastapi import FastAPI
from vm_contracts.models import AnalysisResult, InspectionMetadata, CROP_CODES, VERSION
from vm_ml.interface import pending_result
from vm_server.inspections import router as inspections_router

app = FastAPI(title="VisionMachine Foundation", version=VERSION,
              description="Local development storage; no authentication or diagnostic model.")
app.include_router(inspections_router)

@app.get("/healthz")
def health():
    return {"status": "ok", "stage": "foundation", "model_available": False}

@app.get("/v1/capabilities")
def capabilities():
    return {"schema_version": VERSION, "crop_catalog": CROP_CODES,
            "validated_diagnostic_crops": [], "model_available": False,
            "implemented": ["metadata_validation", "local_image_upload", "local_storage", "local_inspection_lookup"],
            "pending": ["authentication", "inference", "history", "delete"]}

@app.post("/v1/dev/validate-inspection", response_model=AnalysisResult)
def validate_inspection(metadata: InspectionMetadata):
    # Validates structure only. There are no photo bytes here to verify or store.
    return pending_result(metadata)

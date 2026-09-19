"""Local contract-validation server. No upload, persistence or trained model yet."""
from fastapi import FastAPI
from vm_contracts.models import AnalysisResult, InspectionMetadata, CROP_CODES, VERSION
from vm_ml.interface import pending_result

app = FastAPI(title="VisionMachine Foundation", version=VERSION,
              description="Development-only contract validator; no diagnostic model or photo storage.")

@app.get("/healthz")
def health():
    return {"status": "ok", "stage": "foundation", "model_available": False}

@app.get("/v1/capabilities")
def capabilities():
    return {"schema_version": VERSION, "crop_catalog": CROP_CODES,
            "validated_diagnostic_crops": [], "model_available": False,
            "implemented": ["metadata_validation"],
            "pending": ["image_upload", "storage", "authentication", "inference", "history", "delete"]}

@app.post("/v1/dev/validate-inspection", response_model=AnalysisResult)
def validate_inspection(metadata: InspectionMetadata):
    # Validates structure only. There are no photo bytes here to verify or store.
    return pending_result(metadata)

"""Inference boundary. A trained model will implement Predictor later."""
from typing import Protocol
from vm_contracts.models import AnalysisResult, InspectionMetadata

class Predictor(Protocol):
    def predict(self, metadata: InspectionMetadata, image_bytes: bytes) -> AnalysisResult: ...

def pending_result(metadata: InspectionMetadata) -> AnalysisResult:
    warnings = ["MODEL_NOT_AVAILABLE"]
    if metadata.is_mock:
        warnings.append("MOCK_DATA")
    return AnalysisResult(
        schema_version="0.1.0", inspection_id=metadata.inspection_id,
        status="pending_model", origin="none", is_mock_input=metadata.is_mock,
        outcome=None, model_version=None, model_mode=None, confidence=None,
        evidence=[], cause_candidates=[], warnings=warnings,
    )

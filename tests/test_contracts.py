import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from vm_contracts.models import AnalysisResult, InspectionMetadata, SensorPacket
from vm_ml.interface import pending_result

ROOT = Path(__file__).resolve().parents[1]


def test_examples_validate_in_both_contract_formats(inspection):
    packet = inspection["sensor_packet"]
    metadata = InspectionMetadata.model_validate(inspection)
    for filename, value in [
        ("inspection", inspection),
        ("sensor-packet", packet),
        ("analysis-result", pending_result(metadata).model_dump(mode="json")),
    ]:
        schema = json.loads((ROOT / f"contracts/schemas/{filename}.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    assert metadata.is_mock
    assert SensorPacket.model_validate(packet).mode == "mock"


@pytest.mark.parametrize("field,value", [
    ("soil_raw", 4096), ("soil_raw", True), ("soil_raw", -1),
    ("air_temp_c", float("nan")), ("air_temp_c", float("inf")),
    ("air_temp_c", -274.0), ("air_rh_pct", 101.0),
    ("soil_index", 0.5),
])
def test_invalid_or_uncalibrated_readings_rejected(inspection, field, value):
    inspection["sensor_packet"]["readings"][field] = value
    with pytest.raises(ValidationError):
        InspectionMetadata.model_validate(inspection)


def test_missing_measurement_requires_error(inspection):
    packet = inspection["sensor_packet"]
    packet["readings"]["air_temp_c"] = None
    with pytest.raises(ValidationError, match="error code"):
        SensorPacket.model_validate(packet)
    packet["errors"] = ["AIR_TEMP_READ_FAILED"]
    assert SensorPacket.model_validate(packet).readings.air_temp_c is None


def test_raw_and_calibrated_values_retained(inspection):
    packet = inspection["sensor_packet"]
    packet["calibration_id"] = "fixture-calibration"
    packet["readings"]["soil_index"] = 0.5
    result = SensorPacket.model_validate(packet)
    assert result.readings.soil_raw == 1500
    assert result.readings.soil_index == 0.5


def test_wrong_inspection_sensor_pair_rejected(inspection):
    inspection["sensor_packet"]["request_id"] = "22222222-2222-4222-8222-222222222222"
    with pytest.raises(ValidationError, match="must match"):
        InspectionMetadata.model_validate(inspection)


def test_timezone_required(inspection):
    inspection["captured_at"] = "2026-09-19T00:00:00"
    with pytest.raises(ValidationError):
        InspectionMetadata.model_validate(inspection)


def test_absent_sensor_needs_reason_and_no_time(inspection):
    inspection["sensor_packet"] = None
    with pytest.raises(ValidationError):
        InspectionMetadata.model_validate(inspection)
    inspection["sensor_received_at"] = None
    inspection["sensor_absence_reason"] = "disconnected"
    assert InspectionMetadata.model_validate(inspection).sensor_packet is None


def test_model_unavailable_never_claims_normal(inspection):
    result = pending_result(InspectionMetadata.model_validate(inspection)).model_dump(mode="json")
    assert result["status"] == "pending_model"
    assert result["outcome"] is None
    assert result["confidence"] is None
    assert "MOCK_DATA" in result["warnings"]
    result["outcome"] = "no_visible_abnormality"
    with pytest.raises(ValidationError, match="cannot contain a diagnosis"):
        AnalysisResult.model_validate(result)


@pytest.mark.parametrize("origin,is_mock", [("mock", False), ("real_model", True)])
def test_mock_predictions_and_inputs_must_be_visible(inspection, origin, is_mock):
    result = pending_result(InspectionMetadata.model_validate(inspection)).model_dump(mode="json")
    result.update(status="completed", origin=origin, is_mock_input=is_mock,
                  model_version="fixture-model", model_mode="rgb",
                  outcome="inconclusive", warnings=[])
    with pytest.raises(ValidationError, match="MOCK_DATA"):
        AnalysisResult.model_validate(result)
    result["warnings"] = ["MOCK_DATA"]
    assert AnalysisResult.model_validate(result).outcome == "inconclusive"


def test_unknown_fields_are_not_silently_dropped(inspection):
    bad = copy.deepcopy(inspection)
    bad["diagnosis"] = "invented"
    with pytest.raises(ValidationError):
        InspectionMetadata.model_validate(bad)

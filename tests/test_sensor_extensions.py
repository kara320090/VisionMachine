"""Synthetic contract fixtures, never measured sensor evidence."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError
from vm_contracts.models import SensorMeasureRequest, SensorPacket

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def extended(inspection):
    packet = copy.deepcopy(inspection["sensor_packet"])
    packet["extensions"] = {
        "schema_version": "0.1.0",
        "optical": {
            "sensor": "AS7341", "i2c_address": 57,
            "raw_counts": [10, 20, 30, 40, 100, 50, 60, 70, 80, 90, 110, 55],
            "channel_order": "F1,F2,F3,F4,CLEAR_1,NIR_1,F5,F6,F7,F8,CLEAR_2,NIR_2",
            "gain_x": 16, "atime": 29, "astep": 599, "integration_time_ms": 50.04,
            "illumination": "ambient", "led_enabled": False, "status2": [0, 0], "saturated": False,
            "started_uptime_ms": 1000, "finished_uptime_ms": 1150,
        },
        "surface_temperature": {
            "sensor": "MLX90614", "i2c_address": 90, "object_raw": 15058, "ambient_raw": 15058,
            "object_temp_c": 28.01, "ambient_temp_c": 28.01, "emissivity_raw": 65535,
            "emissivity": 1.0, "pec_checked": True, "read_uptime_ms": 1151,
        },
    }
    return packet


def test_basic_packet_remains_compatible_without_extension_key(inspection):
    packet = SensorPacket.model_validate(inspection["sensor_packet"])
    assert "extensions" not in packet.model_dump(mode="json")


def test_request_defaults_to_basic_and_accepts_extended(inspection):
    request = dict(schema_version="0.1.0", message_type="measure", request_id=inspection["inspection_id"])
    assert SensorMeasureRequest.model_validate(request).sensor_profile == "basic"
    request["sensor_profile"] = "extended"
    assert SensorMeasureRequest.model_validate(request).sensor_profile == "extended"
    request["sensor_profile"] = "invented"
    with pytest.raises(ValidationError):
        SensorMeasureRequest.model_validate(request)


def test_extensions_validate_and_roundtrip_without_losing_raw_values(extended):
    packet = SensorPacket.model_validate(extended)
    exported = packet.model_dump(mode="json")
    assert exported["extensions"] == extended["extensions"]
    schema = json.loads((ROOT / "contracts/schemas/sensor-packet.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(exported)


@pytest.mark.parametrize("field,value", [
    ("raw_counts", [0] * 11), ("raw_counts", [0] * 11 + [True]),
    ("raw_counts", [0] * 11 + [65536]), ("integration_time_ms", 99.0),
    ("channel_order", "arbitrary"), ("i2c_address", 58), ("led_enabled", True), ("led_enabled", 0),
])
def test_invalid_optical_data_rejected(extended, field, value):
    extended["extensions"]["optical"][field] = value
    with pytest.raises(ValidationError):
        SensorPacket.model_validate(extended)


@pytest.mark.parametrize("field,value", [
    ("object_raw", 0x8001), ("object_temp_c", 38.0), ("pec_checked", False),
    ("emissivity", 0.5), ("emissivity_raw", 0), ("ambient_temp_c", float("nan")), ("pec_checked", 1),
])
def test_invalid_surface_data_rejected(extended, field, value):
    extended["extensions"]["surface_temperature"][field] = value
    with pytest.raises(ValidationError):
        SensorPacket.model_validate(extended)


def test_missing_optional_sensor_needs_error_and_is_not_zero(extended):
    extended["extensions"]["optical"] = None
    with pytest.raises(ValidationError, match="error code"):
        SensorPacket.model_validate(extended)
    extended["errors"] = ["as7341_disconnected"]
    packet = SensorPacket.model_validate(extended)
    assert packet.extensions.optical is None
    assert packet.extensions.surface_temperature.object_raw == 15058


def test_saturation_keeps_raw_values_and_requires_warning(extended):
    optical = extended["extensions"]["optical"]
    optical["raw_counts"][0] = 18000
    with pytest.raises(ValidationError, match="saturation"):
        SensorPacket.model_validate(extended)
    optical["saturated"] = True
    with pytest.raises(ValidationError, match="warning"):
        SensorPacket.model_validate(extended)
    extended["errors"] = ["as7341_saturated"]
    assert SensorPacket.model_validate(extended).extensions.optical.raw_counts[0] == 18000


def test_unknown_extension_fields_rejected(extended):
    extended["extensions"]["optical"]["invented_brix"] = 12
    with pytest.raises(ValidationError):
        SensorPacket.model_validate(extended)

"""Authoritative v0.1.0 contract draft. No medical/agronomic inference here."""
from typing import Annotated, Literal, Self
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, model_validator

VERSION = "0.1.0"
CROP_CODES = ["cherry_tomato", "pepper", "perilla", "lettuce", "bok_choy", "kale", "basil", "rosemary"]
CropCode = Literal["cherry_tomato", "pepper", "perilla", "lettuce", "bok_choy", "kale", "basil", "rosemary"]
Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")]
Hash256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class SensorReadings(Contract):
    soil_adc_bits: Literal[10, 12, 14]
    soil_raw: Annotated[int, Field(strict=True, ge=0)] | None
    soil_index: Annotated[float, Field(strict=True, ge=0, le=1)] | None
    air_temp_c: Annotated[float, Field(strict=True, ge=-273.15)] | None
    air_rh_pct: Annotated[float, Field(strict=True, ge=0, le=100)] | None

    @model_validator(mode="after")
    def valid_adc(self) -> Self:
        if self.soil_raw is not None and self.soil_raw >= 2 ** self.soil_adc_bits:
            raise ValueError("soil_raw exceeds declared ADC resolution")
        return self

class SensorPacket(Contract):
    schema_version: Literal["0.1.0"]
    message_type: Literal["measurement"]
    request_id: UUID
    device_id: Identifier
    boot_id: Identifier
    firmware_version: Annotated[str, Field(min_length=1, max_length=40)]
    sequence: Annotated[int, Field(strict=True, ge=0)]
    uptime_ms: Annotated[int, Field(strict=True, ge=0)]
    mode: Literal["real", "mock"]
    calibration_id: Identifier | None
    readings: SensorReadings
    errors: list[Annotated[str, Field(min_length=1, max_length=80)]]

    @model_validator(mode="after")
    def valid_measurement(self) -> Self:
        if self.readings.soil_index is not None and self.calibration_id is None:
            raise ValueError("soil_index requires calibration_id")
        raw = self.readings
        if any(v is None for v in (raw.soil_raw, raw.air_temp_c, raw.air_rh_pct)) and not self.errors:
            raise ValueError("missing primary readings require an error code")
        return self

class InspectionMetadata(Contract):
    schema_version: Literal["0.1.0"]
    inspection_id: UUID
    subject_id: Identifier
    subject_type: Literal["plant", "fruit"]
    parent_plant_id: Identifier | None
    batch_id: Identifier
    crop_code: CropCode
    captured_at: AwareDatetime
    capture_source: Literal["real", "synthetic"]
    image_sha256: Hash256
    image_media_type: Literal["image/jpeg", "image/png"]
    sensor_packet: SensorPacket | None
    sensor_received_at: AwareDatetime | None
    sensor_absence_reason: Literal["not_acquired", "disconnected", "permission_denied", "read_error"] | None

    @model_validator(mode="after")
    def valid_pairing(self) -> Self:
        if self.subject_type == "plant" and self.parent_plant_id is not None:
            raise ValueError("plant subject must not have parent_plant_id")
        if self.sensor_packet is None:
            if self.sensor_received_at is not None or self.sensor_absence_reason is None:
                raise ValueError("absent sensor requires reason and no receive timestamp")
        else:
            if self.sensor_received_at is None or self.sensor_absence_reason is not None:
                raise ValueError("present sensor requires receive timestamp and no absence reason")
            if self.sensor_packet.request_id != self.inspection_id:
                raise ValueError("sensor request_id must match inspection_id")
        return self

    @property
    def is_mock(self) -> bool:
        return self.capture_source == "synthetic" or (self.sensor_packet is not None and self.sensor_packet.mode == "mock")

class AnalysisResult(Contract):
    schema_version: Literal["0.1.0"]
    inspection_id: UUID
    status: Literal["pending_model", "completed", "failed"]
    origin: Literal["none", "mock", "real_model"]
    is_mock_input: bool
    outcome: Literal["no_visible_abnormality", "suspected_abnormality", "inconclusive"] | None
    model_version: Annotated[str, Field(min_length=1)] | None
    model_mode: Literal["rgb", "sensor", "fusion"] | None
    confidence: Annotated[float, Field(strict=True, ge=0, le=1)] | None
    evidence: list[str]
    cause_candidates: list[str]
    warnings: list[str]

    @model_validator(mode="after")
    def honest_output(self) -> Self:
        if self.status != "completed":
            if self.origin != "none" or any(v is not None for v in (self.outcome, self.model_version, self.model_mode, self.confidence)) or self.evidence or self.cause_candidates:
                raise ValueError("unavailable/failed analysis cannot contain a diagnosis")
        elif self.origin == "none" or self.outcome is None or self.model_version is None or self.model_mode is None:
            raise ValueError("completed result needs origin, outcome and model identity")
        if (self.origin == "mock" or self.is_mock_input) and "MOCK_DATA" not in self.warnings:
            raise ValueError("mock result/input must carry MOCK_DATA warning")
        return self

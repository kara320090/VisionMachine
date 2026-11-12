#include "Calibration.h"

namespace {
// 근거 교정(calibration/) 완료 전에는 false를 유지합니다.
// SensorPacket 규칙: soil_index가 null이 아니면 calibration_id도 반드시 존재해야 합니다.
constexpr bool kEnableGroundedCalibration = false;

// Identifier 형식(영문 소문자·숫자·하이픈)을 준수한 교정 ID 및 기준 ADC 값 (12-bit 기준)
constexpr const char* kCalibrationId = "cal-sen0308-v1";
constexpr uint16_t kGroundedDryAdc = 0;
constexpr uint16_t kGroundedWetAdc = 0;
} // namespace

Calibration::Calibration()
    : isCalibrated_(kEnableGroundedCalibration),
      calibrationId_(kEnableGroundedCalibration ? kCalibrationId : nullptr),
      dryRefRaw_(kGroundedDryAdc),
      wetRefRaw_(kGroundedWetAdc) {}

void Calibration::begin() {
  if (isCalibrated_ && (calibrationId_ == nullptr || dryRefRaw_ <= wetRefRaw_)) {
    isCalibrated_ = false;
    calibrationId_ = nullptr;
  }
}

CalibratedMeasurement Calibration::apply(const RawMeasurement& raw) const {
  CalibratedMeasurement result;
  result.calibration_id = isCalibrated_ ? calibrationId_ : nullptr;
  result.soil_index_valid = false;
  result.soil_index = 0.0f;

  // 근거 교정 전이거나 원시 측정이 실패한 경우 soil_index = null 반환
  if (!isCalibrated_ || result.calibration_id == nullptr || !raw.soil_valid || dryRefRaw_ <= wetRefRaw_) {
    return result;
  }

  float norm = static_cast<float>(static_cast<int32_t>(dryRefRaw_) - static_cast<int32_t>(raw.soil_raw)) /
               static_cast<float>(static_cast<int32_t>(dryRefRaw_) - static_cast<int32_t>(wetRefRaw_));

  result.soil_index = constrain(norm, 0.0f, 1.0f);
  result.soil_index_valid = true;
  return result;
}
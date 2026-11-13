#include "UsbProtocol.h"
#include <bsp_api.h>

namespace {
constexpr const char* kSchemaVersion = "0.1.0";
constexpr const char* kMessageType = "measurement";
constexpr const char* kFirmwareVersion = "uno-r4-0.2.0";
constexpr const char* kMode = "real";
constexpr const char* kFallbackUuid = "00000000-0000-4000-8000-000000000000";
} // namespace

UsbProtocol::UsbProtocol()
    : adcBits_(12),
      sequence_(0) {
  snprintf(deviceId_, sizeof(deviceId_), "uno-r4-minima");
  snprintf(bootId_, sizeof(bootId_), "boot-0001");
}

void UsbProtocol::begin(uint8_t adcBits) {
  adcBits_ = adcBits;
  requestDecoder_.reset();
  sequence_ = 0;
  initHardwareIdentifiers();
}

void UsbProtocol::initHardwareIdentifiers() {
  // RA4M1 칩셋 고유 ID에서 하위 바이트를 추출해 고정 device_id 구성
  const bsp_unique_id_t* uid = R_BSP_UniqueIdGet();
  if (uid != nullptr) {
    snprintf(
        deviceId_,
        sizeof(deviceId_),
        "uno-r4-%04x%04x",
        static_cast<unsigned int>(uid->unique_id_words[2] & 0xFFFFU),
        static_cast<unsigned int>(uid->unique_id_words[3] & 0xFFFFU));
  } else {
    snprintf(deviceId_, sizeof(deviceId_), "uno-r4-minima");
  }

  // 부팅 세션 식별용 boot_id 생성 (전원 재인가/리셋 감지용)
  uint32_t seed = micros() ^ (static_cast<uint32_t>(analogRead(A0)) << 8);
  if (uid != nullptr) {
    seed ^= uid->unique_id_words[0];
  }
  snprintf(bootId_, sizeof(bootId_), "boot-%08lx", static_cast<unsigned long>(seed));
}

bool UsbProtocol::isValidUuidFormat(const String& uuid) const {
  return MeasureRequestDecoder::isCanonicalUuid(uuid.c_str(), uuid.length());
}

bool UsbProtocol::pollRequest(Stream& stream, String& outRequestId, String& outParseError, bool& outExtended) {
  while (stream.available() > 0) {
    const int byte = stream.read();
    if (byte < 0) break;
    MeasureRequest request;
    if (requestDecoder_.feed(static_cast<char>(byte), request)) {
      outRequestId = request.request_id;
      outParseError = request.error != nullptr ? request.error : "";
      outExtended = request.extended;
      return true;
    }
  }
  return false;
}

void UsbProtocol::printJsonString(Stream& stream, const char* str) const {
  stream.print('\"');
  while (*str) {
    if (*str == '\"' || *str == '\\') {
      stream.print('\\');
    }
    stream.print(*str);
    ++str;
  }
  stream.print('\"');
}

void UsbProtocol::sendMeasurementResponse(
    Stream& stream,
    const String& requestId,
    const RawMeasurement& raw,
    const CalibratedMeasurement& cal,
    bool extended) {

  stream.print("{\"schema_version\":");
  printJsonString(stream, kSchemaVersion);

  stream.print(",\"message_type\":");
  printJsonString(stream, kMessageType);

  stream.print(",\"request_id\":");
  printJsonString(stream, requestId.c_str());

  stream.print(",\"device_id\":");
  printJsonString(stream, deviceId_);

  stream.print(",\"boot_id\":");
  printJsonString(stream, bootId_);

  stream.print(",\"firmware_version\":");
  printJsonString(stream, kFirmwareVersion);

  stream.print(",\"sequence\":");
  stream.print(sequence_++);

  stream.print(",\"uptime_ms\":");
  stream.print(raw.measured_uptime_ms);

  stream.print(",\"mode\":");
  printJsonString(stream, kMode);

  stream.print(",\"calibration_id\":");
  if (cal.calibration_id != nullptr) {
    printJsonString(stream, cal.calibration_id);
  } else {
    stream.print("null");
  }

  // readings 객체 시작
  stream.print(",\"readings\":{\"soil_adc_bits\":");
  stream.print(raw.soil_adc_bits);

  stream.print(",\"soil_raw\":");
  if (raw.soil_valid) {
    stream.print(raw.soil_raw);
  } else {
    stream.print("null");
  }

  stream.print(",\"soil_index\":");
  if (cal.soil_index_valid && cal.calibration_id != nullptr) {
    stream.print(cal.soil_index, 4);
  } else {
    stream.print("null");
  }

  stream.print(",\"air_temp_c\":");
  if (raw.sht_valid) {
    stream.print(raw.air_temp_c, 2);
  } else {
    stream.print("null");
  }

  stream.print(",\"air_rh_pct\":");
  if (raw.sht_valid) {
    stream.print(raw.air_rh_pct, 2);
  } else {
    stream.print("null");
  }
  stream.print("}");

  if (extended) printExtensions(stream, raw);

  // errors 배열 시작 (SensorPacket validator 준수: 기본 센서 누락 시 최소 1개 에러 보장)
  stream.print(",\"errors\":[");
  size_t count = raw.error_count;
  if ((!raw.soil_valid || !raw.sht_valid) && count == 0) {
    printJsonString(stream, "missing_primary_reading");
  } else {
    for (size_t i = 0; i < count; ++i) {
      if (i > 0) stream.print(",");
      printJsonString(stream, raw.errors[i]);
    }
  }
  stream.print("]}\n");
}

void UsbProtocol::printExtensions(Stream& stream, const RawMeasurement& raw) const {
  stream.print(",\"extensions\":{\"schema_version\":\"0.1.0\",\"optical\":");
  if (!raw.optical_valid) stream.print("null");
  else {
    stream.print("{\"sensor\":\"AS7341\",\"i2c_address\":57,\"raw_counts\":[");
    for (uint8_t i = 0; i < 12; ++i) { if (i) stream.print(','); stream.print(raw.optical_counts[i]); }
    stream.print("],\"channel_order\":\"F1,F2,F3,F4,CLEAR_1,NIR_1,F5,F6,F7,F8,CLEAR_2,NIR_2\"");
    stream.print(",\"gain_x\":16,\"atime\":29,\"astep\":599,\"integration_time_ms\":50.04");
    stream.print(",\"illumination\":\"ambient\",\"led_enabled\":false,\"status2\":[");
    stream.print(raw.optical_status[0]); stream.print(','); stream.print(raw.optical_status[1]);
    stream.print("],\"saturated\":"); stream.print(raw.optical_saturated ? "true" : "false");
    stream.print(",\"started_uptime_ms\":"); stream.print(raw.optical_started_ms);
    stream.print(",\"finished_uptime_ms\":"); stream.print(raw.optical_finished_ms);
    stream.print('}');
  }
  stream.print(",\"surface_temperature\":");
  if (!raw.surface_valid) stream.print("null");
  else {
    stream.print("{\"sensor\":\"MLX90614\",\"i2c_address\":90,\"object_raw\":"); stream.print(raw.surface_object_raw);
    stream.print(",\"ambient_raw\":"); stream.print(raw.surface_ambient_raw);
    stream.print(",\"object_temp_c\":"); stream.print(raw.surface_object_c, 2);
    stream.print(",\"ambient_temp_c\":"); stream.print(raw.surface_ambient_c, 2);
    stream.print(",\"emissivity_raw\":"); stream.print(raw.surface_emissivity_raw);
    stream.print(",\"emissivity\":"); stream.print(static_cast<float>(raw.surface_emissivity_raw) / 65535.0f, 5);
    stream.print(",\"pec_checked\":true,\"read_uptime_ms\":"); stream.print(raw.surface_read_ms);
    stream.print('}');
  }
  stream.print('}');
}

void UsbProtocol::sendProtocolError(
    Stream& stream,
    const String& requestId,
    const char* errorCode) {

  stream.print("{\"schema_version\":");
  printJsonString(stream, kSchemaVersion);

  stream.print(",\"message_type\":");
  printJsonString(stream, kMessageType);

  stream.print(",\"request_id\":");
  printJsonString(stream, isValidUuidFormat(requestId) ? requestId.c_str() : kFallbackUuid);

  stream.print(",\"device_id\":");
  printJsonString(stream, deviceId_);

  stream.print(",\"boot_id\":");
  printJsonString(stream, bootId_);

  stream.print(",\"firmware_version\":");
  printJsonString(stream, kFirmwareVersion);

  stream.print(",\"sequence\":");
  stream.print(sequence_++);

  stream.print(",\"uptime_ms\":");
  stream.print(millis());

  stream.print(",\"mode\":");
  printJsonString(stream, kMode);

  stream.print(",\"calibration_id\":null");
  stream.print(",\"readings\":{\"soil_adc_bits\":");
  stream.print(adcBits_);
  stream.print(",\"soil_raw\":null,\"soil_index\":null,\"air_temp_c\":null,\"air_rh_pct\":null}");

  stream.print(",\"errors\":[");
  printJsonString(stream, errorCode);
  stream.print("]}\n");
}

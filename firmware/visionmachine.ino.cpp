#include <Arduino.h>
#include "SensorReader.h"
#include "Calibration.h"
#include "UsbProtocol.h"

namespace {
constexpr unsigned long kBaudRate = 115200;
constexpr uint8_t kSoilPin = A0;     // 04번 SEN0308 토양수분 센서 (A0)
constexpr uint8_t kSoilAdcBits = 12; // analogReadResolution 설정과 동일하게 유지 (12-bit: 0~4095)
} // namespace

SensorReader sensorReader(kSoilPin, kSoilAdcBits);
Calibration calibrator;
UsbProtocol usbProtocol;

void setup() {
  Serial.begin(kBaudRate);
  unsigned long startWait = millis();
  while (!Serial && (millis() - startWait < 3000)) {
    ;
  }

  sensorReader.begin();
  calibrator.begin();
  usbProtocol.begin(kSoilAdcBits);
}

void loop() {
  String requestId;
  String requestError;

  if (usbProtocol.pollRequest(Serial, requestId, requestError)) {
    // 요청 파싱 오류가 발생한 경우 계측값은 null, errors 배열에 사유 기록 후 반환
    if (requestError.length() > 0) {
      usbProtocol.sendProtocolError(Serial, requestId, requestError.c_str());
      return;
    }

    // 요청 시점마다 즉시 새로 계측 (오래된 측정 재사용 방지)
    RawMeasurement raw = sensorReader.readFresh();

    // 근거 교정 적용 (교정 전이면 calibration_id: null, soil_index: null)
    CalibratedMeasurement cal = calibrator.apply(raw);

    // SensorPacket 스키마에 맞춘 JSONL 응답 출력
    usbProtocol.sendMeasurementResponse(Serial, requestId, raw, cal);
  }
}
#ifndef USB_PROTOCOL_H
#define USB_PROTOCOL_H

#include <Arduino.h>
#include "SensorReader.h"
#include "Calibration.h"

class UsbProtocol {
public:
  UsbProtocol();

  void begin(uint8_t adcBits);

  bool pollRequest(Stream& stream, String& outRequestId, String& outParseError);

  void sendMeasurementResponse(
      Stream& stream,
      const String& requestId,
      const RawMeasurement& raw,
      const CalibratedMeasurement& cal);

  void sendProtocolError(
      Stream& stream,
      const String& requestId,
      const char* errorCode);

private:
  static constexpr size_t kMaxLineLen = 256;
  char rxBuffer_[kMaxLineLen];
  size_t rxIndex_;

  uint8_t adcBits_;
  uint32_t sequence_;
  char deviceId_[24];
  char bootId_[24];

  void initHardwareIdentifiers();
  bool extractJsonStringValue(const String& json, const char* key, String& outVal) const;
  bool isValidUuidFormat(const String& uuid) const;
  void printJsonString(Stream& stream, const char* str) const;
};

#endif // USB_PROTOCOL_H
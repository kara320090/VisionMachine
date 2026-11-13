#ifndef USB_PROTOCOL_H
#define USB_PROTOCOL_H

#include <Arduino.h>
#include "SensorReader.h"
#include "Calibration.h"
#include "MeasureRequest.h"

class UsbProtocol {
public:
  UsbProtocol();

  void begin(uint8_t adcBits);

  bool pollRequest(Stream& stream, String& outRequestId, String& outParseError, bool& outExtended);

  void sendMeasurementResponse(
      Stream& stream,
      const String& requestId,
      const RawMeasurement& raw,
      const CalibratedMeasurement& cal,
      bool extended = false);

  void sendProtocolError(
      Stream& stream,
      const String& requestId,
      const char* errorCode);

private:
  MeasureRequestDecoder requestDecoder_;

  uint8_t adcBits_;
  uint32_t sequence_;
  char deviceId_[24];
  char bootId_[24];

  void initHardwareIdentifiers();
  bool isValidUuidFormat(const String& uuid) const;
  void printJsonString(Stream& stream, const char* str) const;
  void printExtensions(Stream& stream, const RawMeasurement& raw) const;
};

#endif // USB_PROTOCOL_H

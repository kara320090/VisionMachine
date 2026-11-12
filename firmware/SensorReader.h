#ifndef SENSOR_READER_H
#define SENSOR_READER_H

#include <Arduino.h>
#include <Wire.h>
#include "Adafruit_SHT31.h"

struct RawMeasurement {
  uint32_t measured_uptime_ms;
  uint8_t soil_adc_bits;

  bool soil_valid;
  uint16_t soil_raw;

  bool sht_valid;
  float air_temp_c;
  float air_rh_pct;

  static constexpr size_t kMaxErrors = 4;
  const char* errors[kMaxErrors];
  size_t error_count;

  void addError(const char* err) {
    if (err != nullptr && error_count < kMaxErrors) {
      errors[error_count++] = err;
    }
  }
};

class SensorReader {
public:
  SensorReader(uint8_t soilPin, uint8_t adcBits);

  void begin();
  RawMeasurement readFresh();

private:
  uint8_t soilPin_;
  uint8_t adcBits_;
  uint16_t maxAdcValue_;

  Adafruit_SHT31 sht31_;
  bool shtInitialized_;
  uint8_t activeShtAddr_;

  bool tryInitSht31();
  bool isI2cDevicePresent(uint8_t address);
};

#endif // SENSOR_READER_H
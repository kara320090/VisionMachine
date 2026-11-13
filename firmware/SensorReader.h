#ifndef SENSOR_READER_H
#define SENSOR_READER_H

#include <Arduino.h>
#include <Wire.h>
#include "Adafruit_SHT31.h"
#include "OpticalReader.h"

struct RawMeasurement {
  uint32_t measured_uptime_ms;
  uint8_t soil_adc_bits;

  bool soil_valid;
  uint16_t soil_raw;

  bool sht_valid;
  float air_temp_c;
  float air_rh_pct;

  bool optical_valid;
  uint16_t optical_counts[12];
  uint8_t optical_status[2];
  bool optical_saturated;
  uint32_t optical_started_ms;
  uint32_t optical_finished_ms;

  bool surface_valid;
  uint16_t surface_object_raw;
  uint16_t surface_ambient_raw;
  uint16_t surface_emissivity_raw;
  float surface_object_c;
  float surface_ambient_c;
  uint32_t surface_read_ms;

  static constexpr size_t kMaxErrors = 8;
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
  RawMeasurement readFresh(bool extended = false);

private:
  uint8_t soilPin_;
  uint8_t adcBits_;
  uint16_t maxAdcValue_;

  Adafruit_SHT31 sht31_;
  bool shtInitialized_;
  uint8_t activeShtAddr_;
  OpticalReader optical_;
  bool opticalInitialized_;

  bool tryInitSht31();
  bool isI2cDevicePresent(uint8_t address);
  void readOptical(RawMeasurement& out);
  void readSurface(RawMeasurement& out);
  bool readMlxWord(uint8_t reg, uint16_t& value);
};

#endif // SENSOR_READER_H

#ifndef CALIBRATION_H
#define CALIBRATION_H

#include <Arduino.h>
#include "SensorReader.h"

struct CalibratedMeasurement {
  const char* calibration_id; // 미교정 시 nullptr -> JSON에서 null
  bool soil_index_valid;      // false이면 JSON에서 soil_index: null
  float soil_index;
};

class Calibration {
public:
  Calibration();

  void begin();
  CalibratedMeasurement apply(const RawMeasurement& raw) const;

private:
  bool isCalibrated_;
  const char* calibrationId_;
  uint16_t dryRefRaw_;
  uint16_t wetRefRaw_;
};

#endif // CALIBRATION_H
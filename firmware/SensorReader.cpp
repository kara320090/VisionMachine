#include "SensorReader.h"
#include "SensorMath.h"

SensorReader::SensorReader(uint8_t soilPin, uint8_t adcBits)
    : soilPin_(soilPin),
      adcBits_(adcBits),
      maxAdcValue_((1U << adcBits) - 1U),
      sht31_(Adafruit_SHT31()),
      shtInitialized_(false),
      activeShtAddr_(0x00),
      opticalInitialized_(false) {}

void SensorReader::begin() {
  // soil_adc_bits와 analogReadResolution 설정을 엄격히 일치시킴
  analogReadResolution(adcBits_);
  pinMode(soilPin_, INPUT);

  Wire.begin();
  Wire.setClock(100000); // MLX90614 SMBus and the shared sensor bus.
  tryInitSht31();
}

bool SensorReader::isI2cDevicePresent(uint8_t address) {
  Wire.beginTransmission(address);
  const uint8_t status = Wire.endTransmission();
  // Leave a bus-free interval before probing another address or reinitializing
  // the driver. Back-to-back probes failed on the tested R4/shared-hub setup.
  delay(1);
  return status == 0;
}

bool SensorReader::tryInitSht31() {
  if (isI2cDevicePresent(0x44) && sht31_.begin(0x44)) {
    shtInitialized_ = true;
    activeShtAddr_ = 0x44;
    return true;
  }
  if (isI2cDevicePresent(0x45) && sht31_.begin(0x45)) {
    shtInitialized_ = true;
    activeShtAddr_ = 0x45;
    return true;
  }
  shtInitialized_ = false;
  activeShtAddr_ = 0x00;
  return false;
}

RawMeasurement SensorReader::readFresh(bool extended) {
  RawMeasurement out{};
  out.measured_uptime_ms = millis();
  out.soil_adc_bits = adcBits_;
  out.soil_valid = false;
  out.soil_raw = 0;
  out.sht_valid = false;
  out.air_temp_c = NAN;
  out.air_rh_pct = NAN;
  out.error_count = 0;

  // 1. SEN0308(A0) 실측
  (void)analogRead(soilPin_); // ADC 멀티플렉서 안정화용 더미 리드
  int rawAdc = analogRead(soilPin_);

  if (rawAdc >= 0 && static_cast<uint16_t>(rawAdc) <= maxAdcValue_) {
    out.soil_raw = static_cast<uint16_t>(rawAdc);
    out.soil_valid = true;
  } else {
    out.soil_valid = false;
    out.addError("soil_adc_out_of_range");
  }

  // 2. SEN0334(SHT31) I2C 실측 (분리 후 재연결 시 재초기화 시도)
  if (!shtInitialized_ || !isI2cDevicePresent(activeShtAddr_)) {
    tryInitSht31();
  }

  if (!shtInitialized_) {
    out.sht_valid = false;
    out.addError("sht31_disconnected");
  } else {
    // One conversion and one CRC-checked frame for this temperature/humidity pair.
    float t = NAN;
    float h = NAN;
    const bool readOk = sht31_.readBoth(&t, &h);

    if (readOk && !isnan(t) && !isnan(h) && t >= -40.0f && t <= 125.0f && h >= 0.0f && h <= 100.0f) {
      out.air_temp_c = t;
      out.air_rh_pct = h;
      out.sht_valid = true;
    } else {
      out.sht_valid = false;
      out.addError("sht31_read_failed");
    }
  }

  if (extended) {
    readOptical(out);
    readSurface(out);
  }
  return out;
}

void SensorReader::readOptical(RawMeasurement& out) {
  out.optical_started_ms = millis();
  if (!isI2cDevicePresent(0x39)) {
    opticalInitialized_ = false;
    out.addError("as7341_disconnected");
    return;
  }
  if (!opticalInitialized_ || !optical_.configurationMatches()) opticalInitialized_ = optical_.configure();
  if (!opticalInitialized_) {
    out.addError("as7341_init_failed");
    return;
  }
  out.optical_valid = optical_.readFresh(out.optical_counts, out.optical_status);
  out.optical_finished_ms = millis();
  if (!out.optical_valid) {
    opticalInitialized_ = false;
    out.addError("as7341_read_failed");
    return;
  }
  out.optical_saturated = ((out.optical_status[0] | out.optical_status[1]) & 0x18) != 0;
  for (uint8_t i = 0; i < 12; ++i)
    if (out.optical_counts[i] >= 18000) out.optical_saturated = true;
  if (out.optical_saturated) out.addError("as7341_saturated");
}

bool SensorReader::readMlxWord(uint8_t reg, uint16_t& value) {
  Wire.beginTransmission(0x5A);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) { delay(1); return false; }
  const uint8_t received = Wire.requestFrom(static_cast<uint8_t>(0x5A), static_cast<uint8_t>(3));
  if (received != 3) { while (Wire.available()) Wire.read(); delay(1); return false; }
  const uint8_t low = Wire.read(), high = Wire.read(), pec = Wire.read();
  const uint8_t bytes[] = {0xB4, reg, 0xB5, low, high};
  delay(1);
  if (SensorMath::smbusCrc(bytes, sizeof(bytes)) != pec) return false;
  value = static_cast<uint16_t>(low) | (static_cast<uint16_t>(high) << 8);
  return true;
}

void SensorReader::readSurface(RawMeasurement& out) {
  out.surface_read_ms = millis();
  if (!isI2cDevicePresent(0x5A)) { out.addError("mlx90614_disconnected"); return; }
  if (!readMlxWord(0x07, out.surface_object_raw) || !readMlxWord(0x06, out.surface_ambient_raw) ||
      !readMlxWord(0x24, out.surface_emissivity_raw)) {
    out.addError("mlx90614_read_or_pec_failed");
    return;
  }
  if (!SensorMath::decodeMlxTemperature(out.surface_object_raw, out.surface_object_c) ||
      !SensorMath::decodeMlxTemperature(out.surface_ambient_raw, out.surface_ambient_c) ||
      out.surface_emissivity_raw == 0 || out.surface_object_c < -70 || out.surface_object_c > 380 ||
      out.surface_ambient_c < -40 || out.surface_ambient_c > 125) {
    out.addError("mlx90614_invalid_reading");
    return;
  }
  out.surface_valid = true;
}

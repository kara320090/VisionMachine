#include "SensorReader.h"

SensorReader::SensorReader(uint8_t soilPin, uint8_t adcBits)
    : soilPin_(soilPin),
      adcBits_(adcBits),
      maxAdcValue_((1U << adcBits) - 1U),
      sht31_(Adafruit_SHT31()),
      shtInitialized_(false),
      activeShtAddr_(0x00) {}

void SensorReader::begin() {
  // soil_adc_bits와 analogReadResolution 설정을 엄격히 일치시킴
  analogReadResolution(adcBits_);
  pinMode(soilPin_, INPUT);

  Wire.begin();
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

RawMeasurement SensorReader::readFresh() {
  RawMeasurement out;
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

  return out;
}

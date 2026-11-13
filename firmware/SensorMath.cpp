#include "SensorMath.h"
namespace SensorMath {
uint8_t smbusCrc(const uint8_t* bytes, size_t length) {
  uint8_t crc = 0;
  for (size_t i = 0; i < length; ++i) {
    crc ^= bytes[i];
    for (uint8_t bit = 0; bit < 8; ++bit)
      crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x07) : static_cast<uint8_t>(crc << 1);
  }
  return crc;
}
bool decodeMlxTemperature(uint16_t raw, float& celsius) {
  if ((raw & 0x8000U) != 0 || raw == 0) return false;
  celsius = static_cast<float>(raw) * 0.02f - 273.15f;
  return true;
}
}

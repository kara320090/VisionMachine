#include "SensorMath.h"
#include <cmath>
#include <cstdlib>
#include <iostream>

int main() {
  // Melexis datasheet read-word example: address 0x5A, register 0x07,
  // returned raw word 0x3AD2, PEC 0x30. Independent published test vector.
  const uint8_t published[] = {0xB4, 0x07, 0xB5, 0xD2, 0x3A};
  if (SensorMath::smbusCrc(published, sizeof(published)) != 0x30) return 1;
  uint8_t corrupt[] = {0xB4, 0x07, 0xB5, 0xD3, 0x3A};
  if (SensorMath::smbusCrc(corrupt, sizeof(corrupt)) == 0x30) return 2;
  float temperature = 0;
  if (!SensorMath::decodeMlxTemperature(0x3AD2, temperature) || std::fabs(temperature - 28.01f) > 0.001f) return 3;
  if (SensorMath::decodeMlxTemperature(0x8001, temperature)) return 4;
  if (SensorMath::decodeMlxTemperature(0, temperature)) return 5;
  std::cout << "SMBus PEC and temperature checks passed: 5\n";
}

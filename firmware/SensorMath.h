#ifndef SENSOR_MATH_H
#define SENSOR_MATH_H
#include <stddef.h>
#include <stdint.h>
namespace SensorMath {
uint8_t smbusCrc(const uint8_t* bytes, size_t length);
bool decodeMlxTemperature(uint16_t raw, float& celsius);
}
#endif

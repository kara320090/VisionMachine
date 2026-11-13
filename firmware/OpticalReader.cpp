#include "OpticalReader.h"
#include <string.h>

bool OpticalReader::startGroup(bool lowChannels) {
  // Sensor routing register values used by Adafruit AS7341 1.4.1 (BSD).
  // https://github.com/adafruit/Adafruit_AS7341/blob/1.4.1/Adafruit_AS7341.cpp
  static const uint8_t low[20] = {0x30,1,0,0,0,0x42,0,0,0x50,0,0,0,0x20,4,0,0x30,1,0x50,0,6};
  static const uint8_t high[20] = {0,0,0,0x40,2,0,0x10,3,0x50,0x10,3,0,0,0,0x24,0,0,0x50,0,6};
  const uint8_t* config = lowChannels ? low : high;
  if (!enableSpectralMeasurement(false)) return false;
  Adafruit_BusIO_Register cfg6(i2c_dev, AS7341_CFG6);
  Adafruit_BusIO_RegisterBits command(&cfg6, 2, 3);
  if (!command.write(AS7341_SMUX_CMD_WRITE)) return false;
  for (uint8_t i = 0; i < 20; ++i) {
    Adafruit_BusIO_Register reg(i2c_dev, i);
    if (!reg.write(config[i])) return false;
  }
  uint8_t actual[20];
  Adafruit_BusIO_Register routing(i2c_dev, 0);
  if (!routing.read(actual, sizeof(actual)) || memcmp(actual, config, sizeof(actual)) != 0) return false;
  Adafruit_BusIO_Register enable(i2c_dev, AS7341_ENABLE);
  Adafruit_BusIO_RegisterBits smux(&enable, 1, 4);
  if (!smux.write(true)) return false;
  const uint32_t start = millis();
  while (millis() - start < 100) {
    uint8_t value = 0;
    if (!enable.read(&value, 1)) return false;
    if (!(value & 0x10)) return enableSpectralMeasurement(true);
    delay(1);
  }
  return false;
}

bool OpticalReader::configure() {
  if (!begin(0x39, &Wire)) return false;
  return setATIME(29) && setASTEP(599) && setGain(AS7341_GAIN_16X) &&
         enableLED(false) && configurationMatches();
}

bool OpticalReader::configurationMatches() {
  return getATIME() == 29 && getASTEP() == 599 && getGain() == AS7341_GAIN_16X;
}

bool OpticalReader::waitReady() {
  const uint32_t start = millis();
  while (millis() - start < 500) {
    Adafruit_BusIO_Register status(i2c_dev, 0xA3);
    uint8_t value = 0;
    if (!status.read(&value, 1)) return false;
    if (value & 0x40) return true;
    delay(1);
  }
  return false;
}

bool OpticalReader::readGroup(uint16_t* counts, uint8_t& status) {
  Adafruit_BusIO_Register data(i2c_dev, AS7341_CH0_DATA_L);
  Adafruit_BusIO_Register state(i2c_dev, 0xA3);
  uint8_t bytes[12];
  if (!data.read(bytes, sizeof(bytes)) || !state.read(&status, 1)) return false;
  for (uint8_t i = 0; i < 6; ++i)
    counts[i] = static_cast<uint16_t>(bytes[2 * i]) | (static_cast<uint16_t>(bytes[2 * i + 1]) << 8);
  return true;
}

bool OpticalReader::readFresh(uint16_t* counts, uint8_t* status) {
  bool ok = startGroup(true) && waitReady() && readGroup(counts, status[0]) &&
            startGroup(false) && waitReady() && readGroup(counts + 6, status[1]);
  if (!enableSpectralMeasurement(false)) ok = false;
  return ok;
}

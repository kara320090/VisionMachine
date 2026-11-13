#ifndef OPTICAL_READER_H
#define OPTICAL_READER_H
#include <Adafruit_AS7341.h>

// Checked SMUX configuration and block reads with finite waits. The upstream
// blocking readAllChannels() waits forever and its async cache drops errors.
class OpticalReader : public Adafruit_AS7341 {
public:
  bool configure();
  bool configurationMatches();
  bool readFresh(uint16_t* counts, uint8_t* status);
private:
  bool waitReady();
  bool startGroup(bool lowChannels);
  bool readGroup(uint16_t* counts, uint8_t& status);
};
#endif

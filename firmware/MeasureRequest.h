#ifndef MEASURE_REQUEST_H
#define MEASURE_REQUEST_H

#include <stddef.h>

struct MeasureRequest {
  char request_id[37];
  const char* error;  // nullptr means a valid request; never a measured value.
  bool extended;
};

// Bounded JSONL decoder: three required fields and optional sensor_profile.
// Independent of Arduino so the exact firmware decoder can be tested on a PC.
class MeasureRequestDecoder {
public:
  static constexpr size_t kMaxLineBytes = 255;  // Excludes LF; includes optional CR.
  MeasureRequestDecoder();
  void reset();
  bool feed(char byte, MeasureRequest& out);
  static bool isCanonicalUuid(const char* text, size_t length);

private:
  char line_[kMaxLineBytes + 1];
  size_t length_;
  bool dropping_;
  bool parse(MeasureRequest& out) const;
};

#endif

#include "MeasureRequest.h"
#include <string.h>

namespace {
constexpr const char* kFallbackUuid = "00000000-0000-4000-8000-000000000000";

void initializeResult(MeasureRequest& out) {
  memcpy(out.request_id, kFallbackUuid, 37);
  out.error = nullptr;
  out.extended = false;
}

struct Token {
  const char* text;
  size_t length;
  bool equals(const char* expected) const {
    return length == strlen(expected) && memcmp(text, expected, length) == 0;
  }
};

class Cursor {
public:
  Cursor(const char* text, size_t length) : next_(text), end_(text + length) {}
  void whitespace() {
    while (next_ != end_ && (*next_ == ' ' || *next_ == '\t' || *next_ == '\r')) ++next_;
  }
  bool take(char expected) {
    whitespace();
    if (next_ == end_ || *next_ != expected) return false;
    ++next_;
    return true;
  }
  bool atEnd() { whitespace(); return next_ == end_; }
  bool string(Token& token) {
    if (!take('"')) return false;
    token.text = next_;
    while (next_ != end_ && *next_ != '"') {
      const unsigned char c = static_cast<unsigned char>(*next_);
      // Protocol fields are literal ASCII: no escapes, control bytes or UTF-8.
      if (c < 0x20 || c > 0x7e || c == '\\') return false;
      ++next_;
    }
    if (next_ == end_) return false;
    token.length = static_cast<size_t>(next_ - token.text);
    ++next_;
    return true;
  }
private:
  const char* next_;
  const char* end_;
};
} // namespace

MeasureRequestDecoder::MeasureRequestDecoder() { reset(); }

void MeasureRequestDecoder::reset() {
  length_ = 0;
  dropping_ = false;
}

bool MeasureRequestDecoder::isCanonicalUuid(const char* text, size_t length) {
  if (length != 36) return false;
  for (size_t i = 0; i < length; ++i) {
    const char c = text[i];
    if (i == 8 || i == 13 || i == 18 || i == 23) {
      if (c != '-') return false;
    } else if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) {
      return false;
    }
  }
  return true;
}

bool MeasureRequestDecoder::feed(char byte, MeasureRequest& out) {
  if (dropping_) {
    if (byte == '\n') reset();
    return false;
  }
  if (byte == '\n') {
    const bool ready = parse(out);
    length_ = 0;
    return ready;
  }
  if (length_ == kMaxLineBytes) {
    length_ = 0;
    dropping_ = true;  // Keep discarding across USB chunks until this line ends.
    initializeResult(out);
    out.error = "request_line_too_long";
    return true;
  }
  line_[length_++] = byte;
  return false;
}

bool MeasureRequestDecoder::parse(MeasureRequest& out) const {
  initializeResult(out);
  Cursor cursor(line_, length_);
  if (cursor.atEnd()) return false;  // Ignore blank lines.
  out.error = "invalid_jsonl_request";
  if (!cursor.take('{')) return true;

  unsigned int fields = 0;
  const char* fieldError = nullptr;
  if (!cursor.take('}')) {
    do {
      Token key{}, value{};
      if (!cursor.string(key) || !cursor.take(':') || !cursor.string(value)) return true;
      unsigned int bit = 0;
      if (key.equals("schema_version")) {
        bit = 1;
        if (!value.equals("0.1.0")) fieldError = "invalid_schema_version";
      } else if (key.equals("message_type")) {
        bit = 2;
        if (!value.equals("measure")) fieldError = "invalid_message_type";
      } else if (key.equals("request_id")) {
        bit = 4;
        if (isCanonicalUuid(value.text, value.length)) {
          memcpy(out.request_id, value.text, 36);
          out.request_id[36] = '\0';
        } else {
          fieldError = "invalid_request_id_uuid";
        }
      } else if (key.equals("sensor_profile")) {
        bit = 8;
        if (value.equals("extended")) out.extended = true;
        else if (!value.equals("basic")) fieldError = "invalid_sensor_profile";
      } else {
        fieldError = "unknown_request_field";
      }
      if ((fields & bit) != 0) fieldError = "duplicate_request_field";
      fields |= bit;
      if (cursor.take('}')) break;
      if (!cursor.take(',')) return true;
    } while (true);
  }
  if (!cursor.atEnd()) return true;
  if (fieldError != nullptr) out.error = fieldError;
  else if ((fields & 4) == 0) out.error = "missing_request_id";
  else if ((fields & 7) != 7) out.error = "missing_request_field";
  else out.error = nullptr;
  return true;
}

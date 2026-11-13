#include "MeasureRequest.h"
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {
const std::string kId = "12345678-1234-4234-8234-abcdef123456";
const std::string kFields[] = {
    "\"schema_version\":\"0.1.0\"", "\"message_type\":\"measure\"",
    "\"request_id\":\"" + kId + "\""};
const std::string kRequest = "{" + kFields[0] + "," + kFields[1] + "," + kFields[2] + "}";
int checks = 0;

void require(bool value, const char* message) {
  ++checks;
  if (!value) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}

std::vector<MeasureRequest> feed(MeasureRequestDecoder& decoder, const std::string& bytes) {
  std::vector<MeasureRequest> events;
  for (char byte : bytes) {
    MeasureRequest result{};
    if (decoder.feed(byte, result)) events.push_back(result);
  }
  return events;
}

void reject(const std::string& line) {
  MeasureRequestDecoder decoder;
  const auto events = feed(decoder, line + '\n' + kRequest + '\n');
  require(events.size() == 2 && events[0].error != nullptr, "invalid request must be rejected");
  require(events[1].error == nullptr, "valid next line must recover after rejection");
}
} // namespace

int main() {
  // All field orders, whitespace and both line endings emitted by serial tools.
  int order[] = {0, 1, 2};
  do {
    for (const std::string& ending : {std::string("\n"), std::string("\r\n")}) {
      MeasureRequestDecoder decoder;
      const auto events = feed(decoder, " \t{ " + kFields[order[0]] + " , " +
          kFields[order[1]] + " , " + kFields[order[2]] + " }\t" + ending);
      require(events.size() == 1 && events[0].error == nullptr, "valid field order/whitespace");
      require(events[0].request_id == kId, "request ID preserved");
    }
  } while (std::next_permutation(order, order + 3));

  // Every possible two-chunk split, then multiple requests in a single chunk.
  for (size_t cut = 0; cut <= kRequest.size(); ++cut) {
    MeasureRequestDecoder decoder;
    require(feed(decoder, kRequest.substr(0, cut)).empty(), "partial request must not measure");
    const auto events = feed(decoder, kRequest.substr(cut) + '\n');
    require(events.size() == 1 && events[0].error == nullptr, "fragmented request must reassemble");
  }
  MeasureRequestDecoder decoder;
  require(feed(decoder, "\n\r\n \t\n" + kRequest + '\n' + kRequest + '\n').size() == 2,
          "blank lines ignored and multiple valid requests preserved");

  reject("{" + kFields[2] + "}");  // Old code accepted a UUID without type/version.
  reject("{\"schema_version\":\"9.0.0\"," + kFields[1] + "," + kFields[2] + "}");
  reject("{" + kFields[0] + ",\"message_type\":\"erase\"," + kFields[2] + "}");
  reject("{" + kFields[0] + "," + kFields[1] + "}");
  reject("{" + kFields[0] + "," + kFields[1] + ",\"request_id\":null}");
  reject("{" + kFields[0] + "," + kFields[1] + ",\"request_id\":\"invalid\"}");
  reject("{" + kFields[0] + "," + kFields[1] + ",\"request_id\":\"12345678-1234-4234-8234-ABCDEF123456\"}");
  reject(kRequest.substr(0, kRequest.size() - 1) + ",\"extra\":\"value\"}");
  reject(kRequest.substr(0, kRequest.size() - 1) + "," + kFields[2] + "}");
  reject(kRequest.substr(0, kRequest.size() - 1) + ",}");
  reject(kRequest + "garbage");
  reject(kRequest + kRequest);
  reject("{\"wrapper\":" + kRequest + "}");
  reject("{'schema_version':'0.1.0','message_type':'measure','request_id':'" + kId + "'}");
  reject("{" + kFields[0] + " " + kFields[1] + "," + kFields[2] + "}");
  auto corrupt = kRequest;
  corrupt.insert(corrupt.find("measure") + 3, 1, '\r');
  reject(corrupt);  // CR inside a string must not be silently deleted.
  corrupt = kRequest;
  corrupt.insert(corrupt.find("request_id"), 1, '\0');
  reject(corrupt);  // No C-string truncation at embedded NUL.
  reject("{\"schema_version\":\"0.1.0\",\"message_type\":\"meas\\u0075re\"," + kFields[2] + "}");

  // Boundary and interrupted oversized line. Its tail may itself look valid.
  decoder.reset();
  const size_t padding = MeasureRequestDecoder::kMaxLineBytes - kRequest.size();
  auto events = feed(decoder, kRequest + std::string(padding, ' ') + '\n');
  require(events.size() == 1 && events[0].error == nullptr, "exact maximum line accepted");
  events = feed(decoder, std::string(MeasureRequestDecoder::kMaxLineBytes + 1, 'x'));
  require(events.size() == 1 && std::string(events[0].error) == "request_line_too_long",
          "overflow produces one error immediately");
  require(feed(decoder, kRequest).empty(), "overflow tail in later USB chunk must not measure");
  require(feed(decoder, std::string(600, 'x') + '\n').empty(), "overflow reported only once");
  events = feed(decoder, kRequest + '\n');
  require(events.size() == 1 && events[0].error == nullptr, "recover only at real line boundary");

  feed(decoder, "unfinished");
  decoder.reset();
  require(feed(decoder, kRequest + '\n')[0].error == nullptr, "reset discards partial state");
  require(!feed(decoder, kRequest + '\n')[0].extended, "legacy request remains basic");
  const std::string extended = kRequest.substr(0, kRequest.size() - 1) + ",\"sensor_profile\":\"extended\"}";
  events = feed(decoder, extended + '\n');
  require(events.size() == 1 && events[0].error == nullptr && events[0].extended,
          "extended sensors require an explicit profile request");
  events = feed(decoder, kRequest.substr(0, kRequest.size() - 1) + ",\"sensor_profile\":\"basic\"}\n");
  require(events.size() == 1 && events[0].error == nullptr && !events[0].extended, "explicit basic profile");
  reject(kRequest.substr(0, kRequest.size() - 1) + ",\"sensor_profile\":\"invented\"}");
  reject(extended.substr(0, extended.size() - 1) + ",\"sensor_profile\":\"basic\"}");
  std::cout << "Measure request regression checks passed: " << checks << '\n';
}

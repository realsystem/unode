// Renogy Rover over the BT-1 module: request builder, frame reassembly and CRC check.
// Protocol source (cited, community project): https://github.com/mavenius/renogy-bt-esphome
// Modbus RTU, device 255, function 3, read 34 words from register 0x0100 -> 73-byte answer.
// A BLE notification can be shorter than the answer (default 20-byte chunks), so chunks are joined here.
#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>

namespace camper {

static const size_t FRAME_LEN = 73;   // 3 header + 68 data + 2 CRC

static std::vector<uint8_t> rx;       // answer being collected
static std::vector<uint8_t> frame;    // last complete answer with a good CRC
static uint32_t rx_first_ms = 0;
static uint32_t bad_frames = 0;

inline uint16_t crc16(const uint8_t *d, size_t n) {
  uint16_t c = 0xFFFF;
  for (size_t i = 0; i < n; i++) {
    c ^= d[i];
    for (int b = 0; b < 8; b++) c = (c & 1) ? (c >> 1) ^ 0xA001 : c >> 1;
  }
  return c;
}

inline std::vector<uint8_t> request() {
  std::vector<uint8_t> r = {0xFF, 0x03, 0x01, 0x00, 0x00, 0x22};
  uint16_t c = crc16(r.data(), r.size());
  r.push_back(c & 0xFF);          // CRC low byte first
  r.push_back(c >> 8);
  return r;
}

// Call once per request, before sending it.
inline void start_request(uint32_t now_ms) {
  rx.clear();
  rx_first_ms = now_ms;
}

// Feed one notification. Returns 1 when a complete answer with a good CRC is now in `frame`,
// -1 when a complete answer had a bad CRC (dropped), 0 when more data is needed.
inline int feed(const std::vector<uint8_t> &chunk) {
  rx.insert(rx.end(), chunk.begin(), chunk.end());
  if (rx.size() < FRAME_LEN) return 0;
  if (rx.size() > FRAME_LEN) rx.resize(FRAME_LEN);
  uint16_t want = rx[FRAME_LEN - 2] | (rx[FRAME_LEN - 1] << 8);
  bool ok = rx[0] == 0xFF && rx[1] == 0x03 && crc16(rx.data(), FRAME_LEN - 2) == want;
  if (ok) frame = rx; else bad_frames++;
  rx.clear();
  return ok ? 1 : -1;
}

inline uint16_t u16(size_t off) { return ((uint16_t) frame[off] << 8) | frame[off + 1]; }
inline uint32_t u32(size_t off) { return ((uint32_t) u16(off) << 16) | u16(off + 2); }

// Temperature byte: bit 7 = sign, low 7 bits = degrees C.
inline float temp_c(uint8_t raw) { return (raw & 0x80) ? -(float) (raw & 0x7F) : (float) raw; }

inline const char *charge_state(uint8_t s) {
  switch (s) {
    case 0: return "off";
    case 1: return "activated";
    case 2: return "MPPT";
    case 3: return "equalizing";
    case 4: return "boost";
    case 5: return "float";
    case 6: return "current limit";
    default: return "unknown";
  }
}

}  // namespace camper

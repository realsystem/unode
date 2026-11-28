# UNODE ↔ SNODE compatibility note

UNODE and SNODE (soil-moisture nodes, https://github.com/realsystem/snode) are separate projects
that must stay compatible (owner decision, 2026-11-25). The reference copy of this contract is
`docs/11-unode-compat.md` in the SNODE repo (design log D45 there). Change both in the same change set.

## Independence
- UNODE never requires the SNODE receiver; it may use it once it exists.
- SNODE never depends on UNODE (a UNODE may host the receiver function only as an option).
- No shared hardware purchases: the owner's ESP32-C3 order is for SNODE only.

## Shared radio path (iteration 2: decided by owner, 2026-11-25)
- UNODE nodes report over ESP-NOW to the SNODE receiver at the trailer (LoRa deferred until both projects are field-tested), with SNODE's channel follow
  (the node saves its last good channel; on a missed acknowledgement it scans channels 1-11).
- Pump node is about 90 m (~300 ft) from the trailer; SNODE's worst-case link is 105 m.
  UNVERIFIED for the pump site: needs a walk test there.
- ESP-NOW costs much less energy per report than Wi-Fi + MQTT (SNODE measured about 7.7 mC vs 108.6 mC).
- The SNODE receiver has no UNODE handling yet; forwarding UNODE packets to HA is future receiver work.
- Iteration 1 UNODE stays on Wi-Fi + MQTT.

## Packet namespace (byte 0 = type, byte 1 = version)
| Type | Direction | Owner |
|---|---|---|
| 0x01, 0x02 | node → receiver | SNODE (report, install list) |
| 0x81 | receiver → node | SNODE (time + next wake) |
| **0x10-0x1F** | node → receiver | **UNODE (reserved)** |
| **0x90-0x9F** | receiver → node | **UNODE (reserved)** |
- The SNODE POC receiver drops any type other than 0x01/0x02 (VERIFIED by reading its code).

## HA and IDs
- Node IDs: `unode_<purpose>_<nn>`, e.g. `unode_gen_01`, `unode_pump_01` (SNODE uses `snode_<grove>_<nn>`).
- HA event `esphome.unode_report` is reserved for UNODE packets forwarded by the receiver.
- Iteration-2 entity pattern: `sensor.battery_unode_<id>`, `binary_sensor.online_unode_<id>`.
  Iteration 1 uses MQTT discovery names ("Generator running", "Node status"); aligning them is open.

## Power variant terms (shared)
- **Solar only**: panel + supercapacitor, no battery. **Battery only**: primary cells (e.g. lithium AA), no charging.
- `unode_pump`: **solar only** (owner, 2026-11-25). It runs in daylight only, like the pump; HA must treat
  night silence as normal, and freeze alerts come from the weather station.
- `unode_gen`: **battery only** (owner, 2026-11-25): primary lithium cells, no charging. It wakes on the
  generator's USB/AC 5 V change (start/stop) and on a timer (heartbeat + starter-battery reading).

## Reused from SNODE (owner: minimize work, reuse ideas and findings)
Proposed, all UNVERIFIED until bench tests; details live in the SNODE repo.
| UNODE need | Reuse from SNODE | SNODE ref |
|---|---|---|
| MCU for iteration 2 | ESP32-C3 (XIAO ESP32C3 on the bench); ESP8266 stays iteration-1 POC only | D5, D44 |
| `unode_gen` pack | 3x Energizer L91 AA, reverse-polarity P-FET, pack voltage divider read only while awake | D6 variant B, `08-node-design.md` |
| `unode_gen` wake | **G1 (owner decision):** ESP32-C3 deep sleep, GPIO level wake on the 5 V sense (opposite level armed before sleep) + timer. ~1.3 mAh/day with ESP-NOW, ~5 years on 3x L91 (UNVERIFIED; measure board sleep current with SNODE's T2 method). G2 (SNODE RTC power gating) rejected: needs an edge-detect circuit for multi-day runs, no practical life gain | D11, D23 |
| `unode_pump` storage | Supercapacitor + TI BQ25570 harvester + TPS61099 boost: fits the light-sensor version; the camera version (~0.9 W) is beyond it: open | D28, D23, variant A |
| Radio | ESP-NOW to the SNODE receiver, channel follow | D27, D30, D31 |
| ESP-NOW bench results | ESP32 to ESP32 test, 0 % loss over one hour at 1-3 m, cold-start search about 170 s; clean link to 20 m through walls and a yard, edge near -93 dBm, 30 m mostly lost; router-channel-change test still open | SNODE docs/poc-espnow-bench.md |
| Receiver | Same receiver firmware gains UNODE packet types 0x10-0x1F (one firmware, not two) | `firmware/receiver/` |
| Tests | Sleep/off current method (T2), walk-test method (T9/T12) at the pump and generator spots | `05-poc-plan.md` |

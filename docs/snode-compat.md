# UNODE ↔ SNODE compatibility note

UNODE and SNODE (soil-moisture nodes, https://github.com/realsystem/snode) are separate projects
that must stay compatible (owner decision, 2026-11-25). The reference copy of this contract is
`docs/11-unode-compat.md` in the SNODE repo (design log D45 there). Change both in the same change set.

## Independence
- UNODE never requires the SNODE receiver; it may use it once it exists.
- SNODE never depends on UNODE (a UNODE may host the receiver function only as an option).
- No shared hardware purchases: the owner's ESP32-C3 order is for SNODE only.

## Shared radio path (option, iteration 2)
- UNODE nodes may report over ESP-NOW to the SNODE receiver at the trailer, with SNODE's channel follow
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
- `unode_gen`: **open**. It must also monitor the starter battery while the generator is off.
  Battery only with timed wakes (starter battery read on each heartbeat) is under review.

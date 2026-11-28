# UNODE camper node (iteration 2): standalone solar charger monitor, plan

A node that lives inside a small truck camper, reads the Renogy Rover 40 charge controller over its Bluetooth
module, and shows the data on the owner's phone **without a Raspberry Pi and without Home Assistant (HA)**.
Later the same node takes other vehicle sensors (see "Later add-ons").

Claims are marked VERIFIED (owner, vendor or cited source) or UNVERIFIED (needs a test).
Status: design only, decided 2026-11-28. No firmware written yet.

## Owner decisions (VERIFIED, from the owner)

| Topic | Decision |
|---|---|
| Controller | Renogy Rover 40 with the **BT-1** Bluetooth module (phone app already works with it) |
| Power | Camper 12 V, through a fuse and a 12 V to 5 V converter |
| Phone link | Either the node's **own Wi-Fi hotspot** or **joining the camper's Starlink Wi-Fi**. The phone talks to the node either way. The phone app is designed later |
| HA | **Also** report to the home HA (MQTT) when the camper is in range of home Wi-Fi. HA is optional, never required |

## Why this is a different kind of node

The other nodes follow "node, then Wi-Fi/ESP-NOW, then HA does the logging and alerting". The camper node
must work with nothing else running, so it breaks three rules of the farm design. This is intended and only
applies to this node (CLAUDE.md has a matching note):

| Farm rule | Camper node |
|---|---|
| HA does all logging and alerting | The node keeps a short history itself and serves it to the phone |
| MQTT only, no ESPHome native API | The phone interface is the node's own HTTP/event stream (see "Phone interface"); MQTT is used only for the optional home HA link |
| Powered by solar/primary cells, tiny budget | Powered by the camper battery it monitors, so its own draw matters (see "Power") |

Kept from the farm design: monitoring only (no wiring into the controller), stable HA entity names, tunables in
`substitutions`, node id `unode_camper_01`, SNODE/UNODE contract untouched (this node does not use ESP-NOW and does
not need the SNODE receiver).

## Architecture

```
Rover 40 --RJ12--> BT-1 dongle ~~BLE~~> ESP32 (unode_camper_01) ~~Wi-Fi~~> phone app (later)
                                           |                         \--> home HA over MQTT (optional)
                                           +-- 12 V fuse -> 5 V buck (camper battery)
```

- **Board: ESP32 (classic or C3), not ESP8266.** The ESP8266 has no Bluetooth. ESP32 does BLE and Wi-Fi on one
  radio; ESPHome's BLE client is meant to coexist with Wi-Fi at the default scan settings (VERIFIED, comment in
  the cited community config). Throughput and stability with BLE, hotspot and station running together are
  UNVERIFIED: first bench test.
- **No wiring to the controller.** Only the BT-1's own wireless link is used, so the Rover is never modified.
- **BT-1 allows one Bluetooth connection at a time (UNVERIFIED, usual for BLE peripherals).** While the node is
  connected, the Renogy phone app probably cannot connect to the same BT-1. The node's own phone app replaces it.
  Test: connect the node, then try the Renogy app.

## Reading the Rover (BT-1 protocol)

VERIFIED from the cited community project ([mavenius/renogy-bt-esphome](https://github.com/mavenius/renogy-bt-esphome),
tested there with a Rover on a BT module, ESPHome BLE client):

- Write the request to service `FFD0`, characteristic `FFD1`. Notifications come back on service `FFF0`,
  characteristic `FFF1`.
- Request (Modbus RTU, device 255, function 3): read 34 words from register `0x0100`. Poll every 30 s there.
- Answer is 73 bytes or more. Fields (big-endian words, byte offsets in the answer):

| Value | Offset | Scale |
|---|---|---|
| Battery state of charge | 3 | 1 % |
| Battery voltage | 5 | 0.1 V |
| Battery (charge) current | 7 | 0.01 A |
| Controller / battery temperature | 9 / 10 | 1 °C, bit 7 = negative |
| Load voltage / current / power | 11 / 13 / 15 | 0.1 V / 0.01 A / 1 W |
| PV voltage / current / power | 17 / 19 / 21 | 0.1 V / 0.01 A / 1 W |
| Max charge / discharge power today | 33 / 35 | 1 W |
| Charge / discharge Ah today | 37 / 39 | 1 Ah |
| Generation / consumption today | 41 / 43 | 1 Wh |
| Generation total | 59 (4 bytes) | 0.001 kWh |
| Load on/off | byte 67, bit 7 | |
| Charging state | byte 68 | 0 off, 1 activated, 2 MPPT, 3 equalize, 4 boost, 5 float, 6 current limit |

- Same register block is used by the Python reader [cruscio/renogy-bt](https://github.com/cruscio/renogy-bt)
  (Rover/Wanderer series). Not yet checked against the owner's Rover: UNVERIFIED until the bench test.
- Fault and alarm bits (registers near `0x0121`) and the battery type (`0xE004`) are in the Renogy Modbus
  document. They are **not** in the cited config: UNVERIFIED, to be added after reading the Renogy document.
- The same project can switch the load output (Modbus write to `0x010A`). Not in v1: monitoring only. If added,
  off by default, with a confirm step in the phone app.
- The module's Bluetooth address (MAC) is needed once. It is read from a scan, not from the repo. Never commit it.

## Phone interface

The app comes later, so the node must offer an interface that stays stable and works the same on the node's
hotspot and on Starlink Wi-Fi:

- **Same address either way:** mDNS name `unode-camper-01.local` plus a fixed fallback address on the hotspot
  (192.168.4.1 is the usual default ESP hotspot address: UNVERIFIED for ESPHome 2026.11, check on the bench).
- **Interface:** ESPHome `web_server` (HTTP REST `GET /sensor/<id>` and a live event stream), entity ids frozen
  like the HA names. The app is a client of that; a plain browser page works from day one. Whether the ESPHome
  native API is a better fit for the app is open (see Open items).
- **Hotspot and Starlink at once:** ESPHome starts the hotspot only as a fallback when the Wi-Fi client cannot
  connect (UNVERIFIED for 2026.11; to confirm). Planned behavior: join Starlink if it is in range, otherwise
  start the hotspot after a timeout. A switch to force the hotspot is a later option.
- **Security:** hotspot password and web page login are set in `secrets.yaml` (never committed). Anything the app
  can change (load switch, later) needs its own login.
- **History:** the app asks for it, the node does not need HA. Keep a ring buffer in RAM (for example 5-minute
  samples for 24 h) and daily totals from the controller (generation today, Ah today). Survives only until a
  restart; flash storage of history is a later decision (flash wear, see CLAUDE.md persisted counters rule).

## Optional home HA link

- When the node joins the home Wi-Fi (the same Wi-Fi client slot as Starlink: a list of networks, strongest first),
  it also publishes to the home Mosquitto broker with MQTT discovery. Names (stable):
  "Camper battery voltage", "Camper battery percentage", "Camper PV power", "Camper charging state",
  "Camper generation today", "Node status".
- If the broker is unreachable, nothing else changes: standalone is the normal mode.
- Starlink and home Wi-Fi in the same node means a list of known networks; ESPHome supports several `networks:`.
  Which one wins when both are in range: UNVERIFIED, prefer the home one by order in the list.

## Power (UNVERIFIED arithmetic)

- An ESP32 with Wi-Fi hotspot and BLE client draws roughly 100 to 150 mA at 5 V (about 0.5 to 0.75 W).
  Through a buck converter at 85 % that is about 0.6 to 0.9 W from the 12 V battery, about 1.2 to 1.8 Ah/day.
- On a small camper battery that is noticeable if the camper sits unused for weeks. Options for later:
  Wi-Fi power-save when no phone is connected, polling every 30 to 60 s, or a low-voltage cut-off
  (turn the node off below about 11.8 V; number to be set from the battery chemistry, UNVERIFIED).
- The node must tolerate vehicle 12 V: 5 V buck rated for at least 24 V input (load-dump spikes), a fuse near the
  battery, and a reverse-polarity diode. Battery chemistry and capacity: owner to say.

## Steps

1. **Bench: read the Rover.** ESP32 devkit on USB, ESPHome config based on the cited project, log the raw answer in
   the camper next to the Rover. Compare each value with the Renogy phone app. Record the BT-1 address.
2. **Bench: Wi-Fi + BLE together.** Phone on the hotspot while the node reads the Rover every 5 s. Check dropped
   reads and web page latency. Then the same on Starlink Wi-Fi.
3. **Firmware:** `esphome/unode-camper-poc.yaml` with the values above, stable entity ids, MQTT as optional.
4. **Fault bits and battery type** from the Renogy Modbus document.
5. **Install:** fused 12 V feed, 5 V buck, small box, antenna position away from the metal roof if possible.
6. **Phone app** (separate design).

## Later add-ons (not designed yet)

Second battery or chassis voltage (ADC with a resistor divider), fridge or cabin temperature, door switch,
tilt/shock sensor, GPS, a relay for a load. Each one gets its own entry here when the owner picks it. Anything that
connects to the vehicle's wiring (OBD-II, CAN) is read-only unless the owner decides otherwise.

## Open items

- Rover 40 firmware version and whether the BT-1 is the original one: ask the owner to look at the Renogy app.
- Battery type (lead-acid, AGM, LiFePO4) and size: sets cut-off voltage and the "low battery" alert level.
- Phone interface choice: ESPHome `web_server` stream vs ESPHome native API for the future app.
- Hotspot plus Starlink behavior, and which network wins at home (see above).
- Where the node sits in the camper (BLE range to the Rover, Wi-Fi coverage).

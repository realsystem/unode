# UNODE vision add-on (iteration 2): plan

An optional ESP32-CAM module that reads a controller's front-panel lights and reports their
states, so a node can monitor equipment it is not allowed to wire into (first target: the RPS
100V Universal Pump Controller). One **profile** per controller model says where each light is
and what it means.

Claims are marked VERIFIED (owner, vendor or cited source) or UNVERIFIED (needs a test).

## Why (decided 2026-11-24)

- RPS tech support (VERIFIED): the controller drives its probes with a pulsed signal and judges
  water by the signal's response, not by voltage. Terminals: Tank full = COM 2 + TH, Well low = COM 1 + WH.
- So **no electrical tap on the probe wires**: any added path could make the controller read
  "wet" and run the pump dry. Reading the controller's own indicator lights is non-invasive.
- Owner decisions (VERIFIED): has an ESP32-CAM; accepts a larger pump-node panel (~10 W) and 4+ cells
  for the camera version; panel photo of the controller comes later.
- Iteration 1 pump node can use 1-2 light sensors (photodiode/LDR on ADS1115 channels) for
  "Well low" and "Pump running" instead of a camera.

## Architecture

- **Core node** (always on, low power): events, heartbeats, battery, LoRa/Wi-Fi uplink.
- **Vision add-on** (ESP32-CAM): powered by the core only in daylight (the solar-direct pump
  cannot run at night). Takes frames, measures brightness in each light's region, decides
  on / off / blinking, and reports only **states** (a few bytes) to the core over UART, or
  directly over MQTT where Wi-Fi reaches.
- Images never go over LoRa. Images are only for setup, viewed over Wi-Fi or a phone hotspot on site.
- The same profile drives a cheaper backend: one light sensor per light on an ADS1115 channel.

## Power (UNVERIFIED arithmetic, from AI-Thinker figures)

- AI-Thinker: about 180 mA at 5 V with flash off; deep sleep about 6 mA at 5 V; supply 4.75-5.25 V.
- Continuous in daylight: 0.9 W x 8 h / 0.85 boost efficiency = about 8.5 Wh, plus night sleep
  0.03 W x 16 h = 0.5 Wh, **about 9 Wh/day** (iteration-1 node: about 2.1 Wh/day).
- Sizing: panel about 10 W, 4+ x 18650, and a 5 V boost converter (the 3.3 V buck of the
  iteration-1 charger board cannot power the ESP32-CAM).
- Lower-power option: wake every 30-60 s for one frame; alert delay grows to that interval.

## Profile format (draft)

```yaml
# profiles/<maker>-<model>.yaml
profile: rps-100v-universal          # id
model: "RPS 100V Universal Pump Controller"
frame:                                # how the camera sees the panel
  resolution: 800x600
  reference: { x: 0, y: 0 }           # optional alignment mark, for small camera shifts
indicators:
  - id: pump_running
    name: "Pump running"              # HA entity name, keep stable
    roi: { x: 120, y: 80, w: 16, h: 16 }   # region in the frame, pixels
    color: green                      # optional: check hue, not only brightness
    on_level: 60                      # brightness 0-255 above which the light is ON
    blink: { min_period_ms: 300, max_period_ms: 2000 }   # optional
    meaning: { on: "running", off: "stopped", blink: "starting / fault" }
  - id: well_low
    name: "Well low"
    roi: { x: 120, y: 120, w: 16, h: 16 }
    on_level: 60
# backend: sensor -> each indicator gets `channel: ads1115_a0` instead of `roi`
```

Placeholder coordinates: the RPS profile is filled in from the front-panel photo.

## Steps

1. **Camera check (bench, USB 5 V):** flash `esphome/unode-vision-camcheck.yaml`, open the
   stream and snapshot pages, check focus at the planned distance, measure current with a
   USB meter if available.
2. **Test target:** point it at any device with status lights (router, charger) and check that
   lights are clearly separable from the background, with the flash LED off.
3. **Light-reading firmware:** per-region brightness, on/off/blink decision, MQTT with HA
   discovery, states over UART for the core. ESPHome's camera component only sends images to
   HA over the native API, so this needs our own firmware or an ESPHome external component.
4. **First profile:** `profiles/rps-100v-universal.yaml` from the panel photo.
5. **Field test:** glare, daylight changes, cold (ESP32-CAM rated -20 to 70 C: UNVERIFIED in an
   unheated controller box), condensation on the lens.

## Open items

- Controller front-panel photo: which lights exist, steady or blinking, colors.
- Flashing the ESP32-CAM: needs an ESP32-CAM-MB USB base or a USB-serial adapter (GPIO0 to GND to flash).
- Mounting: fixed bracket, no movement between camera and panel; shade from direct sun.
- Firmware choice for step 3: ESPHome external component vs. standalone Arduino/ESP-IDF sketch.

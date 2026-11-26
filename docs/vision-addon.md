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

LED column in the manufacturer's front-panel photo (VERIFIED, from the photo): seven lights, top to
bottom POWER, PUMP, MPPT, ERROR, LOW PWR, TANK FULL, WELL LOW. As fractions of the enclosure's outer
rectangle (about 423 x 615 px in that photo): column at x = 0.775 of the width from the left edge,
POWER at y = 0.283 of the height from the top, pitch 0.044 of the height.

## RPS front panel: observed behavior (from RPS videos)

Sources (VERIFIED, manufacturer channel "RPS Solar Pumps"):
- "Pro Builder Explains: The Best Add-On for Off-Grid Solar Well Pumps",
  https://www.youtube.com/watch?v=Y8KyG-82_uo, 0:26-1:30 (close-up of the panel).
- "Tour Jared's Homestead & Livestock Solar-Powered Water Set Up: RPS 800, RPS 200 & 110V Converter",
  https://www.youtube.com/watch?v=BD27DEwsAQo, 25:00-32:00 (panel on a shed wall, small in frame).

Method: the product photo of the panel was matched to every frame (SIFT features + homography, 30 fps),
which maps each frame onto the photo so each LED position is known. The close-up clip matched in 63 % of
frames (the rest: hand in front, camera moves, blur). Frames and the photo are the manufacturer's
material and are not stored in this repo.

Modes seen (VERIFIED, seen on the frames; the mode names are UNVERIFIED, inferred from the labels):

| Mode | POWER | PUMP | MPPT | TANK FULL | Where |
|---|---|---|---|---|---|
| Pumping | green, steady | green, steady | green, **blinking** (about 1.0 s on / 1.2 s off) | off | Y8Ky video, 0:26-0:40 |
| Tank full | green, steady | off | off | **red**, steady | Y8Ky video, about 0:50 to 1:30 |

Other observations:
- Lit LEDs are green or red. In the video the centre of a lit LED looks white because the camera
  overexposes it; the glow around the centre keeps the LED's colour. There are no white LEDs on the
  panel (owner). Judge the colour of the glow, not the centre. **Unlit LEDs look amber/yellow** (their
  lens colour), not dark, so "yellowish" must not count as on. VERIFIED (seen on the frames).
- Glare on the label or enclosure can make non-LED spots look bright. Judge each light by brightness
  against its neighbors **and** hue, not brightness alone. VERIFIED (it produced false "on" readings).
- ERROR, LOW PWR and WELL LOW were never seen lit in about 8 minutes of video. Their colors and behavior
  are unknown. UNVERIFIED: needs the RPS manual or a fault test.
- Blink timing is from only a few cycles (about 2.2 s per cycle, +/- 0.2 s). UNVERIFIED. Whether PUMP
  blinks while starting was not seen.
- Sampling once per second hid the MPPT blink in the tour video (the lit bar seemed to change length).
  The reader needs at least 4 frames/s over a window of at least 5 s to tell steady from blinking.
  UNVERIFIED as a requirement; it follows from the cycle above.

Implications for the profile (UNVERIFIED):
- Raise `blink.max_period_ms` from 2000 to about 3000 (the observed cycle is about 2.2 s).
- MPPT blinking while pumping is normal, so a blink on MPPT must not raise a fault.
- Colors: POWER, PUMP, MPPT green; TANK FULL red.

## Camera check: bench notes (2026-11-25)

- VERIFIED: `esphome/unode-vision-camcheck.yaml` compiles, flashes and serves a valid 800x600 JPEG at
  `:8081` (stream at `:8080`).
- VERIFIED: right after flashing, the log repeated `Got invalid frame from camera!` and the snapshot
  failed. Re-seating the camera ribbon (power off, lift the latch, push the ribbon fully in) fixed it.
  The camera had passed its probe, so a bad probe is not the only sign of a loose ribbon.
- VERIFIED: flashing the ESP32-CAM with a CP2102 USB-serial adapter (3.3 V logic): adapter TXD to U0R,
  RXD to U0T, +5V to 5V, GND to GND, IO0 to GND while powering up. DTR is not connected, so there is no
  auto-reset: power-cycle the camera (pull and replug the 5V wire) to reset it. To run, remove the IO0
  jumper and power-cycle.
- VERIFIED: wiring check before flashing. With IO0 grounded at power-up, the boot ROM prints
  `boot:0x3 (DOWNLOAD_BOOT...) waiting for download` on U0T at 115200. Seeing it proves power, ground,
  IO0 and the camera-to-adapter wire.
- VERIFIED failure: an ESP8266 NodeMCU as the adapter (RST to GND, TX to U0R, RX to U0T) gave
  `No serial data received`. A community post suggests TX to TX and RX to RX for that trick; not tested
  here. UNVERIFIED.
- VERIFIED on the Windows dev PC: ESPHome ESP32 builds failed on Python 3.15 (ESP-IDF needs the
  `windows-curses` package, which has no build for it). Use Python 3.12 in a virtual environment. Set
  `ESPHOME_ESP_IDF_PREFIX` to a short path such as `C:\ESPHome\idf`, because the default toolchain path
  is longer than Windows' 260-character limit and gives errors like `bits/c++config.h: No such file`.
- VERIFIED on the same PC: antivirus HTTPS scanning (Avast Web Shield) re-signs downloads, so Python
  tools failed with `CERTIFICATE_VERIFY_FAILED` for github.com, githubusercontent.com, platformio.org,
  espressif.com and pypi.org until those hosts were excluded from HTTPS scanning.

## ESP32-CAM on a weak Wi-Fi link: findings (bench, 2026-11-25)

Why: a user's Wi-Fi may be weak and we cannot ask them to move the router or add power. Reading a
blinking light needs at least 4 frames/s (see "RPS front panel"). With the default
`unode-vision-camcheck.yaml` the camera streamed at only 0.1-0.5 frames/s (about 9 kB/s), ping to
it had a median of 115-215 ms with 3-10 % loss, and an over-the-air update took 220 s (VERIFIED, measured).

Method: one setting changed at a time, flashed over the air, then measured the same way: 30 pings
and two 20 s runs of the MJPEG stream (port 8080). A change was kept only if it was at least 1.3x
faster. One board, one router, one scene (a phone showing the panel), short runs.

| Change (all vs. the baseline) | Frames/s | Data rate | Ping median / worst | Result |
|---|---|---|---|---|
| Baseline: camera clock 20 MHz, power save off | 0.32 | 9 kB/s | 19.5 / 183 ms | |
| Camera clock 10 MHz | 0.05 | 1.3 kB/s | 84.5 / 620 ms | worse |
| Camera clock **8 MHz** | **4.6** | 122 kB/s | **8.5 / 59 ms** | kept |
| Wi-Fi TX power 20 dB (on top of 8 MHz) | 4.57 | 120 kB/s | 7.5 / 15 ms | no change |
| Wi-Fi TX power 15 dB (on top of 8 MHz) | 4.74 | 123 kB/s | 7.0 / 30 ms | no change |
| Frames 320x240, JPEG quality 25 (on top of 8 MHz) | **8.6** | 39 kB/s | 10 / 30 ms | kept |
| Larger Wi-Fi/TCP buffers | not run | | | queue stopped at the 5 frames/s target |

Findings:
- VERIFIED (this board): lowering the camera clock from 20 to 8 MHz made the stream 14x faster and cut
  ping latency by more than half with the same router, position and power. The camera's own clock was
  interfering with its Wi-Fi radio. Several forum reports describe the same (clock noise coupling into the
  antenna, fixed by a lower clock, shielding or a ground plane).
- VERIFIED: 10 MHz was worse than 20 MHz. UNVERIFIED explanation: harmonics of the clock landing inside the
  router's channel. So treat the camera clock as a calibration to check per site and Wi-Fi channel, not as a
  constant. Not tested: other channels, other routers, other boards.
- VERIFIED: TX power (15 or 20 dB) made no difference once the interference was removed.
- UNVERIFIED: `power_save_mode: none` helped. It was set before the measurements and not isolated.
- VERIFIED: 320x240 doubled the frame rate again (4.6 to 8.6) but each LED is then only a few pixels
  wide, about 14 px apart, so neighbouring glows overlap. With a fixed brightness threshold a steady LED
  next to a blinking one read as blinking (its reading moved between about 19 and 27). Decide steady or
  blinking from how much each LED's reading swings over time (blinking MPPT: about 35, steady POWER: about 8).
- VERIFIED (method): with the camera on a phone showing the pumping animation (1.0 s on / 1.2 s off), the
  camera measured 0.99 s on / 1.19 s off, a 2.18 s cycle over 13 cycles at 8.6 frames/s. This checks the
  camera, the fix and the timing method, not the real controller.
- VERIFIED: the snapshot page (port 8081) is slow (about one frame per 5 s) because ESPHome's camera runs
  fast only while a stream is requested. Use the stream (port 8080) for timing. Leaving connections
  half-open stalled the camera for tens of seconds.
- Not tested: antenna selection or an external antenna, a separate stronger 5 V supply, larger Wi-Fi/TCP
  buffers (`sdkconfig_options`), other router channels.

Repeat test (same board, router and scene; tuned build vs original, each freshly flashed over the air):
- VERIFIED: tuned build (8 MHz clock, 320x240) A1 8.19-8.62 frames/s (mean 8.47), original build (20 MHz,
  800x600) 1.17-1.18, tuned build again A2 8.04-8.62 (mean 8.42). Ping median 7-8.5 ms and worst case 31 ms or
  less for the tuned build, 12-15 ms and up to 109 ms for the original. 0 % ping loss in all of these rounds.
  The tuned build stayed fast after both reboots.
- VERIFIED: the original build is not only slow but unpredictable: 0.05-0.5 frames/s in the first tests,
  0.32 in the queue, 1.17 here, always below the 4 frames/s a blink needs. The gap to the tuned build ranged
  from about 7x to 27x depending on the moment.
- VERIFIED: five timings of the phone animation's blink (1.00 s on / 1.20 s off): 0.94-1.03 s on, 1.17-1.21 s
  off, cycle 2.15-2.21 s, 10-13 complete cycles each. In four of the five runs POWER and PUMP read steady; in
  the first, POWER showed spurious transitions from neighbouring glow (see above).
- Raw data and tables: `tools/cam-link-test/results/`. Still one board, one router, one channel, about 25
  minutes of repeats: UNVERIFIED for other sites.

Design consequences (UNVERIFIED):
- A weak link should not carry video. Read the lights on the camera and send only the result (a few
  bytes by MQTT or ESP-NOW). ESPHome 2026.11 has an `on_image` trigger on `esp32_camera`, but the camera
  only captures fast while a stream is requested (idle rate is at most 1 frame/s), so continuous reading at 4+
  frames/s probably needs a small custom component that requests frames itself.
- Keep the camera-clock check in the bring-up procedure for each site.

Sources: [Random Nerd Tutorials, external antenna](https://randomnerdtutorials.com/esp32-cam-connect-external-antenna/),
[Espressif, Wi-Fi Performance and Power Save](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi-driver/wifi-performance-and-power-save.html),
[ESPHome WiFi component](https://esphome.io/components/wifi/),
[esp32.com, recommended XCLK values](https://esp32.com/viewtopic.php?p=142317),
[esp32.com, weird WiFi behaviour](https://esp32.com/viewtopic.php?p=17021),
[Home Assistant forum, ESP32-CAM stability](https://community.home-assistant.io/t/esp32-cam-stability/281712),
[esp32-camera issue 172](https://github.com/espressif/esp32-camera/issues/172).
To repeat the test, see `tools/cam-link-test/README.md` (experiment driver, link measurement and blink timing scripts).

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

- Controller front-panel behavior: POWER, PUMP, MPPT and TANK FULL are known (see "RPS front panel:
  observed behavior"). Still open: ERROR, LOW PWR and WELL LOW (colors, steady or blinking), and whether
  PUMP blinks while starting.
- Flashing the ESP32-CAM: done with a CP2102 USB-serial adapter (see "Camera check: bench notes"); an
  ESP32-CAM-MB USB base also works. GPIO0 to GND to flash.
- Camera clock vs Wi-Fi channel: find out whether the best clock depends on the router channel, and
  whether the firmware should test or select it at boot. Also try an external antenna and a separate 5 V supply.
- Light-reading on the camera: a custom component that requests frames and reports each light's state
  (steady/blinking/off) over MQTT or ESP-NOW, so no video has to cross a weak link.
- Mounting: fixed bracket, no movement between camera and panel; shade from direct sun.
- Firmware choice for step 3: ESPHome external component vs. standalone Arduino/ESP-IDF sketch.

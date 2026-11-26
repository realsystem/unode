# cam-link-test: measure and tune the ESP32-CAM's Wi-Fi link

Reproduces the bench test in `docs/vision-addon.md` ("ESP32-CAM on a weak Wi-Fi link"): measure how
fast the camera streams, change one setting at a time over the air, keep what helps, and time a
blinking light as the camera sees it.

| File | What it does |
|---|---|
| `measure_link.py` | Ping loss/latency plus MJPEG stream frames/s and kB/s of a running camera. Standard library only. |
| `run_experiments.py` | Hands-off queue: edit a copy of the config, validate, flash over the air, measure, keep a change only if it clearly helps, flash the best settings at the end. |
| `blink_probe.py` | Finds the lit LEDs in the stream by itself and times each one's on/off periods. Needs `numpy`, `opencv-python-headless`. |

Our raw data and result tables are in `results/` (see `results/README.md`).

Status: the numbers in the docs came from one board, one router and one scene. UNVERIFIED that other
setups give the same ranking. The scripts were checked on the same bench (dry run of all seven configs,
live `measure_link.py` 8.59 frames/s, live `blink_probe.py` 2.20 s cycle).

## 1. Set up the Windows PC (once)
1. **Python 3.12 for ESPHome.** ESP32 builds fail on Python 3.15 (ESP-IDF needs `windows-curses`, which
   has no build for it). Create a virtual environment and install the same version we used:
   `py -3.12 -m venv C:\ESPHome\venv312` then `C:\ESPHome\venv312\Scripts\python -m pip install esphome==2026.11.0`.
2. **Short ESP-IDF path.** `setx ESPHOME_ESP_IDF_PREFIX C:\ESPHome\idf` (the default tools folder is longer than
   Windows' 260-character path limit). Open a new terminal afterwards.
3. **Antivirus.** HTTPS scanning (for example Avast Web Shield) made downloads fail with
   `CERTIFICATE_VERIFY_FAILED`. Exclude github.com, githubusercontent.com, platformio.org, espressif.com
   and pypi.org from HTTPS scanning.
4. **Secrets.** `esphome/secrets.yaml` from `esphome/secrets.yaml.example` (never commit it).
5. For `blink_probe.py`: `python -m pip install numpy opencv-python-headless`.

## 2. Put the original firmware on the camera
The experiments flash over the air, so the camera must be on the network first. Flash
`esphome/unode-vision-camcheck.yaml` once over USB (see "Camera check: bench notes" in
`docs/vision-addon.md` for the CP2102 adapter wiring) and re-seat the camera ribbon if the log shows
`Got invalid frame from camera!`. Find its IP (`unode-vision-camcheck.local`).

## 3. Fix the scene
Do not move anything during a run. The test target we used was a phone on its side showing the RPS panel
animation (1.0 s on / 1.2 s off MPPT blink); the animation is made from the manufacturer's photo and is
not stored here. Any steady green LED beside a blinking one works for `blink_probe.py`. Close every
browser tab that shows the camera stream or snapshot, and do not run two measurements at once: the camera
serves one stream at a time and stalls for tens of seconds after a half-open connection.

## 4. Check the queue (no camera needed)
From the repo root:
```
python tools\cam-link-test\run_experiments.py --dry-run --esphome-python C:\ESPHome\venv312\Scripts\python.exe --out %TEMP%\camtest
```
Every experiment should print `valid (dry run)`. It writes a temporary copy of the config
(`esphome\unode-vision-camcheck-linktest.yaml`) and deletes it afterwards; the tracked file is never edited.

## 5. Run it
```
python tools\cam-link-test\run_experiments.py --host <camera-ip> --esphome-python C:\ESPHome\venv312\Scripts\python.exe --out %TEMP%\camtest
```
- Takes 1 hour or more. Each step is a compile, an over-the-air update (25 s to a few minutes on a lossy
  link) and a measurement (30 pings, two 20 s stream runs 25 s apart).
- Experiments: E0 baseline (20 MHz camera clock, 800x600, power save off); E1a/E1b clock 10 and 8 MHz;
  E2a/E2b Wi-Fi TX power 20 and 15 dB; E3 frames 320x240 at JPEG quality 25; E4 bigger Wi-Fi/TCP buffers.
- A change is kept for the later experiments only if it is at least 1.3x faster than the best so far. The
  run stops early at `--target` frames/s (default 5; E4 was never run in our test).
- Results: `<out>\results.jsonl` (one line per experiment) and `<out>\best_camcheck.yaml`. The camera is left
  on the best settings. To keep them, copy the changed values into the tracked config (and a PR).

To measure any camera by hand: `python tools\cam-link-test\measure_link.py <camera-ip> 20 2`.

## 6. Time a blink
```
python tools\cam-link-test\blink_probe.py <camera-ip> 30
```
It prints each light's lit share and swing, and the MPPT cycle. Compare with the target's real timing
(ours: 1.00 s on / 1.20 s off; the camera measured 0.99 / 1.19 and 1.03 / 1.17 over 13 and 11 cycles).

## 7. Reading the results
- Expect the baseline to be slow if the camera clock interferes with Wi-Fi (ours: 0.3 frames/s, ping median
  about 20 ms with outliers over 180 ms). Reading a blink needs 4 frames/s or more.
- Our ranking: clock 8 MHz (4.6 frames/s) >> 20 MHz (0.3) > 10 MHz (0.05); TX power no effect; 320x240 (8.6).
- 10 MHz being worse than 20 MHz suggests the best clock depends on the router's Wi-Fi channel
  (UNVERIFIED). To test: change the router's 2.4 GHz channel and run E0, E1a and E1b again.
- If no setting helps, the cause may be elsewhere: the board's antenna selection (an external-antenna
  resistor), a weak 5 V supply, or distance. None of these were tested.

## Pitfalls we hit
- The snapshot page (port 8081) gives about one frame per 5 s; always measure the stream (port 8080).
- Fixed exposure did not help and made the LEDs dimmer; Wi-Fi power saving off alone did not help.
- Over-the-air flashing needs the same `ota_password` the camera was built with.
- Glow from neighbouring LEDs overlaps at 320x240 (about 14 px between LEDs): judge a light by how much
  its reading swings, not by one fixed threshold.

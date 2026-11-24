# Generator node POC: setup guide (iteration 1)

Proof of concept for the generator UNODE: an ESP-12E (ESP8266) devkit and an SW-420
vibration module detect when the generator runs, count run hours, and report to Home Assistant.

- **Windows PC** = dev box: edit, compile, flash, read logs (ESPHome command line).
- **Home Assistant** = integration only: MQTT broker, entities, history, alerts.

Status of the claims here: wiring, pins and HA steps are from the design (VERIFIED by the bench
test of the board and the SW-420 on 2026-11-23). ESPHome command behaviour on Windows,
the alert delays and the running threshold are UNVERIFIED until you run them.

## What you need

| Item | Notes |
|---|---|
| ESP-12E devkit (NodeMCU style, CP2102 USB chip) | Silicon Labs CP210x driver installed on the PC |
| SW-420 vibration module | 3 wires to the devkit |
| Micro-USB data cable | |
| USB power bank | Powers the node at the generator, so it still reports after the generator stops |
| Windows PC with internet | First compile downloads the ESP8266 toolchain |
| Home Assistant (HA OS on the Pi) on the same network | |

Optional, for the AC-lost / overload test later: 10 kΩ and 20 kΩ resistors (see the end).

## 1. Wire the SW-420 (USB unplugged)

| SW-420 | Devkit |
|---|---|
| VCC | 3V3 (not VIN/5V) |
| GND | GND |
| DO | D7 (GPIO13) |

## 2. Set up the Windows dev box (once)

1. Install Python 3 from python.org. In the installer tick **Add python.exe to PATH**.
   Check ESPHome's install page for the minimum Python version.
2. Open **PowerShell** and install ESPHome:
   ```powershell
   python -m pip install esphome
   esphome version
   ```
3. Get the repo onto the PC: `git clone https://github.com/realsystem/unode C:\unode`
   (or download the ZIP from GitHub and unpack it to `C:\unode`). A short path like
   `C:\unode` avoids Windows long-path build errors.
4. Create your secrets file from the example and fill in real values:
   ```powershell
   cd C:\unode\esphome
   copy secrets.yaml.example secrets.yaml
   notepad secrets.yaml
   ```
   `secrets.yaml` is git-ignored. Never commit it. `mqtt_broker` is the HA Pi's IP address,
   `mqtt_user` / `mqtt_password` are the HA user from step 3.
5. Check the config (no board needed):
   ```powershell
   esphome config unode-gen-poc.yaml
   ```

## 3. Set up Home Assistant (integration only)

1. **Settings → Add-ons → Add-on Store → Mosquitto broker**: install, start, enable *Start on boot*.
2. **Settings → People → Users → Add user** `unode` with a password (Mosquitto uses HA users).
3. **Settings → Devices & Services**: configure the discovered **MQTT** integration.
4. Note the Pi's IP under **Settings → System → Network** (for `mqtt_broker`).

The ESPHome add-on is not needed: the node talks MQTT, and HA builds its entities from MQTT discovery.

## 4. First flash over USB

1. Plug the devkit into the PC. Device Manager shows
   **Ports (COM & LPT) → Silicon Labs CP210x USB to UART Bridge (COMx)**.
2. Compile and flash, then follow the logs:
   ```powershell
   cd C:\unode\esphome
   esphome run unode-gen-poc.yaml
   ```
   Pick the COM port when asked. The first compile takes several minutes (toolchain download).
   If it stops at "Connecting...", hold the board's **FLASH** button until writing starts.
3. In the logs, wait for a Wi-Fi IP address and an MQTT connection. Note the IP.

## 5. Later updates over Wi-Fi (no cable)

```powershell
esphome run unode-gen-poc.yaml --device <node IP>
esphome logs unode-gen-poc.yaml --device <node IP>
```
If logs over Wi-Fi don't connect, plug in USB and use `--device COMx`.

## 6. Check it in Home Assistant

**Settings → Devices & Services → MQTT → Devices → UNODE Generator POC** should list:
Vibration pulses per minute, Vibration raw, Generator running, Generator run hours,
WiFi signal, Uptime, Node status, Restart.
If not, read the ESPHome logs for MQTT errors (usually broker IP, user or password).

## 7. Bench calibration

1. Sensor still: **Vibration raw** OFF, **pulses per minute** about 0.
   If raw is ON when still, set `inverted: true` under the GPIO13 `binary_sensor` and re-flash.
2. Tap the table: pulses rise, the module LED blinks.
3. Turn the SW-420 potentiometer until room bumps give few pulses and tapping gives many.

## 8. Install at the generator

1. Fix the SW-420 rigidly to a metal part of the frame (zip ties or strong tape). A loose sensor reads as vibration.
   Keep it away from the muffler and exhaust.
2. Put the devkit in a small dry container, off the floor.
3. Power it from the power bank. If the bank switches off at low current, use one with an always-on / low-current mode.
4. Check **WiFi signal** in HA: -70 dBm or stronger is good, -75 to -80 marginal, below -80 too weak.

## 9. Run test and set the threshold

Record pulses per minute for a few minutes each:

| State | Pulses/min |
|---|---|
| Engine off (windy day too, if possible) | |
| Engine running, idle | |
| Engine running, under load | |

Set `run_threshold` (top of `unode-gen-poc.yaml`) halfway between *off* and *idle*, then update over Wi-Fi (step 5).
Expected delays with the default filters: *Generator running* ON about 30-40 s after start, OFF about 60-70 s after stop
(`delayed_on: 20s`, `delayed_off: 60s`).

## 10. Alerts in Home Assistant

**Settings → Automations → Create**:
- *Generator started*: Generator running → ON, notify.
- *Generator stopped*: Generator running → OFF, notify.
- *Generator node offline*: Node status OFF or unavailable for 2 min, notify.

Starlink sleeps 9 PM-9 AM, so phone push waits until it is up. Add a **persistent notification** action too,
so events are visible in HA locally.

## 11. Record for iteration 2

- Pulses/min off / idle / loaded, the chosen threshold, any false triggers.
- Real alert delays for start and stop.
- Wi-Fi signal in the shed and any dropouts in HA history.
- Run hours survive a reboot (press **Restart** in HA and compare).
- Power bank run time in the cold.

## Optional: AC-lost / overload signal

Generator USB 5 V → 10 kΩ → D5 (GPIO14), and 20 kΩ from D5 to GND (about 3.3 V at the pin).
Then uncomment the GPIO14 block at the end of `binary_sensor:` in `unode-gen-poc.yaml`.
It adds *Generator 5 V present* and *Generator AC lost while running* (engine vibrating, AC gone).

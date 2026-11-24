# UNODE (Universal Node)
- Small self-powered monitoring nodes (ESP + sensors) for simple off-grid equipment (generator, solar well pump), reporting to Home Assistant on a Raspberry Pi 5 at a remote farm. Iteration 1 is a POC on existing ESP8266 devkits + SW-420; iteration 2 hardware is not chosen yet.

## Commands
- No build system, tests, lint or CI exist in the repo yet.
- Dev box is the owner's Windows PC (ESPHome CLI via `python -m pip install esphome`, run from `esphome/`); HA is used only for MQTT/integration, not the ESPHome add-on. Setup guide: docs/poc-generator.md.
- Validate a node config: `esphome config esphome/unode-gen-poc.yaml` (unverified; needs `esphome/secrets.yaml`)
- Compile: `esphome compile esphome/unode-gen-poc.yaml` (unverified)
- Flash over USB / OTA: `esphome run esphome/unode-gen-poc.yaml --device COM3` or `--device <node IP>` (unverified). web.esphome.io in Chrome/Edge is the fallback for a USB flash.
- Logs: `esphome logs esphome/unode-gen-poc.yaml` (unverified)
- Bench sketch: `arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 examples/esp8266_check` (unverified); in Arduino IDE use board "NodeMCU 1.0 (ESP-12E Module)", 115200 baud.
- Offline check that every `!secret` used is in the example file (verified):
  `python3 -c "import re,yaml;u=set(re.findall(r'!secret (\w+)',open('esphome/unode-gen-poc.yaml').read()));print(u-set(yaml.safe_load(open('esphome/secrets.yaml.example'))) or 'ok')"`

## Architecture
- `esphome/` — one ESPHome YAML per node (`unode-gen-poc.yaml` = generator node) + `secrets.yaml.example`.
- `examples/` — standalone Arduino bench sketches; not node firmware.
- Data flow: node → trailer Wi-Fi (2.4 GHz) → MQTT (Mosquitto add-on on the HA Pi) → HA entities via MQTT discovery. HA does all logging and alerting.
- Planned pump node (~300 ft away) must not rely on Wi-Fi: LoRa via a separate Meshtastic module fed over UART (TEXTMSG). Pi-side LoRa receiver is out of scope but assumed present.
- ESP8266 pin map (keep consistent across nodes): SW-420 DO = D7/GPIO13; optional 5 V sense = D5/GPIO14 via 10k/20k divider; GPIO16→RST reserved for timed deep sleep; GPIO15 = optional relay (must be low at boot); GPIO2 = UART1 TX to LoRa.

## Conventions
- Monitoring only by default; control is optional and only via a relay module. Never modify the monitored equipment: generator uses external ports only; starter-battery SAE port is sense-only, never a power source.
- Each node has its own battery + small solar panel; USB is a backup charge path only where a USB source exists.
- Use MQTT, not the ESPHome native API (nodes may sleep; broker LWT gives the offline alert).
- Keep HA-facing entity names stable (automations depend on them): "Generator running", "Generator run hours", "Node status".
- Persisted counters: `globals` with `restore_value` + `preferences: flash_write_interval: 10min` (flash wear).
- Tunables go in `substitutions` (e.g. `run_threshold`), set from field data.
- Design/engineering claims in docs and PRs are marked VERIFIED (from owner or cited source) or UNVERIFIED (needs test).
- Work on a branch and open a PR; do not push to `main` directly.

## Gotchas
- `esphome/secrets.yaml` is required and git-ignored; create it from `esphome/secrets.yaml.example`. Never commit real values.
- ESP8266 cannot wake from deep sleep on a pin (ESPHome supports timer wake only, with GPIO16 wired to RST). Event alerts therefore need the node awake (iteration 1 uses Wi-Fi `power_save_mode`, no deep sleep).
- Devkits draw mA in sleep via the onboard AMS1117 + USB-serial chip; battery tests feed the 3V3 pin from an external regulator.
- GPIO0/2/15 are boot-strapping pins; don't put loads on them that change their boot level.
- SW-420 output polarity varies by module: check `inverted` on the bench.
- Windows flashing needs the Silicon Labs CP210x (or CH340) USB driver.
- Li-ion must not charge below 0 °C: charger needs an NTC on its TS/TH pin; don't remove it.
- Site internet (Starlink) sleeps 9 PM–9 AM; nothing in the design may depend on internet.
- In Claude cloud sessions pip/package installs are blocked, so `esphome`/`arduino-cli` can't be run there; GitHub GraphQL (`gh pr create`) is blocked, use `gh api repos/realsystem/unode/pulls ...`.

## Definition of done
- Every changed node YAML passes `esphome config` (with secrets filled from the example) — run locally if the tool isn't available here, and say so.
- The `!secret` check above prints `ok`.
- No credentials, IPs with passwords or personal data in the diff.
- New hardware/behavior assumptions are labeled VERIFIED/UNVERIFIED.
- Change is on a branch with a PR to `main`.

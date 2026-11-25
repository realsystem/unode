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
- Iteration 2 radio (owner): ESP-NOW to the shared SNODE receiver at the trailer (channel follow), which forwards to HA as `esphome.unode_report`. LoRa/Meshtastic is deferred until the first SNODE/UNODE versions are field-tested.
- Generator node wake (owner: G1): ESP32-C3 deep sleep with GPIO level wake on the 5 V sense (firmware arms the opposite level before sleeping) + timer heartbeat that also reads the starter battery.
- ESP8266 pin map (keep consistent across nodes): SW-420 DO = D7/GPIO13; optional 5 V sense = D5/GPIO14 via 10k/20k divider; GPIO16→RST reserved for timed deep sleep; GPIO15 = optional relay (must be low at boot); GPIO2 = spare (was UART1 TX to LoRa, deferred).

## Conventions
- Monitoring only by default; control is optional and only via a relay module. Never modify the monitored equipment: generator uses external ports only; starter-battery SAE port is sense-only, never a power source.
- Power variants (shared terms with SNODE): pump node = solar only (panel + supercapacitor, daylight only); generator node = battery only (primary lithium AA, no charging; wakes on USB/AC 5 V change and on a timer that also reads the starter battery). Reuse SNODE designs where they fit: docs/snode-compat.md "Reused from SNODE". Iteration 1 POC runs on USB / power bank.
- Node IDs follow `unode_<purpose>_<nn>` (e.g. `unode_gen_01`, `unode_pump_01`).
- Stay compatible with SNODE (https://github.com/realsystem/snode): reserved ESP-NOW packet types 0x10-0x1F / 0x90-0x9F and HA event `esphome.unode_report`. Contract: docs/snode-compat.md (reference copy in the SNODE repo); change both together.
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
- No rechargeable cells in the node designs (gen = primary lithium, pump = supercapacitor). If a Li-ion/LiFePO4 cell is ever added, it must not charge below 0 °C (charger with cold cut-off).
- Site internet (Starlink) sleeps 9 PM–9 AM; nothing in the design may depend on internet.
- In Claude cloud sessions pip/package installs are blocked, so `esphome`/`arduino-cli` can't be run there; GitHub GraphQL (`gh pr create`) is blocked, use `gh api repos/realsystem/unode/pulls ...`.

## Definition of done
- Every changed node YAML passes `esphome config` (with secrets filled from the example) — run locally if the tool isn't available here, and say so.
- The `!secret` check above prints `ok`.
- No credentials, IPs with passwords or personal data in the diff.
- New hardware/behavior assumptions are labeled VERIFIED/UNVERIFIED.
- Change is on a branch with a PR to `main`.

## GitHub Free-plan limits
This repo is public, so GitHub Actions minutes are free here. The account is on the GitHub Free plan and these limits still apply.

- **Workflows:** keep jobs lean. Use `ubuntu-latest`, add `concurrency` with `cancel-in-progress: true` and `timeout-minutes` to new jobs, and set `retention-days` (3-7) on uploaded artifacts. The account-wide cap is 20 concurrent jobs (5 macOS); extra jobs queue.
- **Files:** never commit a file over 50 MiB (GitHub warns) or 100 MiB (the push is blocked). Keep datasets, video, model weights and build output out of git; use Git LFS only if truly needed.
- **GitHub API:** 5,000 requests/hour authenticated (60 unauthenticated), search 30/min, plus secondary limits. Scripts or agents that call the API must paginate, use conditional requests, and not fan out across repos in parallel.

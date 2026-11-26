"""Hands-off A/B queue for the ESP32-CAM link: edit settings, validate, flash over the air, measure.

One setting changes per experiment, always measured the same way (measure_link.py: 30 pings and
two 20 s stream runs). Greedy: a change is kept for the following experiments only if the mean
frame rate is >= 1.3x the best so far (and at least 0.2 fps better). Stops early at --target fps.
At the end it flashes the best settings found.

Experiments change a COPY of the config (esphome/unode-vision-camcheck-linktest.yaml), never the
tracked file. Needs esphome/secrets.yaml, the camera already flashed once (USB) with the same
OTA password, and ESPHome run from the Python 3.12 environment (see README.md).

Usage (from the repo root):
  python tools/cam-link-test/run_experiments.py --host <camera-ip> --esphome-python <python.exe> --out <dir>
  add --dry-run to only generate and validate every experiment's config (no camera needed).
"""
import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from measure_link import measure  # noqa: E402

# Settings of the ORIGINAL bench config (the baseline experiment). Every experiment sets all of
# these explicitly, so the script works whatever values the tracked config currently has.
BASELINE = {"xclk": "20MHz", "frame": ("800x600", 10), "power_save": "none"}

QUEUE = [
    ("E0 baseline (20 MHz clock, 800x600 q10, power save none)", {}),
    ("E1a camera clock 10 MHz", {"xclk": "10MHz"}),
    ("E1b camera clock 8 MHz", {"xclk": "8MHz"}),
    ("E2a output_power 20 dB", {"output_power": "20dB"}),
    ("E2b output_power 15 dB", {"output_power": "15dB"}),
    ("E3 smaller frames 320x240 q25", {"frame": ("320x240", 25)}),
    ("E4 bigger wifi/TCP buffers", {"sdkconfig": {
        "CONFIG_ESP_WIFI_STATIC_RX_BUFFER_NUM": 16, "CONFIG_ESP_WIFI_DYNAMIC_RX_BUFFER_NUM": 32,
        "CONFIG_ESP_WIFI_RX_BA_WIN": 16, "CONFIG_LWIP_TCP_SND_BUF_DEFAULT": 32768,
        "CONFIG_LWIP_TCP_WND_DEFAULT": 32768}}),
]


def sub_one(text, pattern, repl):
    new, n = re.subn(pattern, repl, text, flags=re.M)
    if n != 1:
        raise ValueError(f"expected exactly one match for {pattern!r}, found {n}")
    return new


def apply_settings(text, s):
    """Return the config text with the settings s applied (values replaced or lines inserted)."""
    t = sub_one(text, r"^(\s+frequency:\s*)\S+", r"\g<1>" + s["xclk"])                 # external_clock
    t = sub_one(t, r"^(\s+resolution:\s*)\S+", r"\g<1>" + s["frame"][0])
    t = sub_one(t, r"^(\s+jpeg_quality:\s*)\S+", r"\g<1>" + str(s["frame"][1]))
    wifi_lines = {"power_save_mode": s["power_save"]}
    if "output_power" in s:
        wifi_lines["output_power"] = s["output_power"]
    for key, val in wifi_lines.items():
        if re.search(rf"^\s+{key}:", t, flags=re.M):
            t = sub_one(t, rf"^(\s+{key}:\s*)\S+", r"\g<1>" + str(val))
        else:
            t = sub_one(t, r"^(\s+password: !secret wifi_password\n)", rf"\g<1>  {key}: {val}\n")
    if "sdkconfig" in s:
        opts = "".join(f'      {k}: "{v}"\n' for k, v in s["sdkconfig"].items())
        t = sub_one(t, r"^(esp32:\n  board: esp32cam\n)",
                    r"\g<1>" + "  framework:\n    type: esp-idf\n    sdkconfig_options:\n" + opts.replace("\\", "\\\\"))
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", help="camera IP (not needed with --dry-run)")
    ap.add_argument("--yaml", default="esphome/unode-vision-camcheck.yaml")
    ap.add_argument("--esphome-python", required=True, help="python.exe of the Python 3.12 environment with esphome")
    ap.add_argument("--idf-prefix", default=r"C:\ESPHome\idf", help="short ESP-IDF tools path (Windows)")
    ap.add_argument("--out", required=True, help="folder for results.jsonl and best_camcheck.yaml")
    ap.add_argument("--target", type=float, default=5.0, help="stop early at this many frames/s")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run and not a.host:
        ap.error("--host is required unless --dry-run")
    os.makedirs(a.out, exist_ok=True)

    esp_dir = os.path.dirname(os.path.abspath(a.yaml))
    work_name = "unode-vision-camcheck-linktest.yaml"
    work = os.path.join(esp_dir, work_name)           # same folder so !secret resolves
    env = dict(os.environ, ESPHOME_ESP_IDF_PREFIX=a.idf_prefix)
    base_text = open(a.yaml, encoding="utf-8").read()

    def sh(cmd, timeout):
        return subprocess.run(cmd, cwd=esp_dir, env=env, capture_output=True, text=True, timeout=timeout)

    def validate():
        r = sh([a.esphome_python, "-m", "esphome", "config", work_name], 300)
        txt = r.stdout + r.stderr
        return "Configuration is valid" in txt, txt[-300:]

    def ota():
        t0 = time.time()
        for attempt in range(3):                      # a weak link can lose a first attempt
            r = sh([a.esphome_python, "-m", "esphome", "run", work_name, "--device", a.host, "--no-logs"], 1500)
            if "OTA successful" in r.stdout + r.stderr:
                return True, time.time() - t0, attempt + 1
        return False, time.time() - t0, 3

    def wait_up(limit=180):
        t0 = time.time()
        while time.time() - t0 < limit:
            try:
                socket.create_connection((a.host, 8080), timeout=3).close()
                time.sleep(12)                        # let the camera settle after boot
                return True
            except OSError:
                time.sleep(3)
        return False

    def log(rec):
        with open(os.path.join(a.out, "results.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)

    adopted = {}
    best_fps = None
    best_name = None
    try:
        for name, change in QUEUE:
            cfg = dict(BASELINE, **adopted, **change)
            rec = {"experiment": name, "settings": cfg}
            open(work, "w", newline="\n", encoding="utf-8").write(apply_settings(base_text, cfg))
            ok, msg = validate()
            if not ok:
                rec.update(status="invalid config", detail=msg)
                log(rec)
                continue
            if a.dry_run:
                rec.update(status="valid (dry run)")
                log(rec)
                continue
            t_start = time.time()
            flashed, secs, tries = ota()
            rec.update(ota_ok=flashed, ota_seconds=round(secs), ota_tries=tries)
            if not flashed or not wait_up():
                rec.update(status="flash or boot failed")
                log(rec)
                continue
            rec.update(measure(a.host))
            fps = rec["fps_mean"]
            if best_fps is None:
                best_fps, best_name, rec["decision"] = fps, name, "baseline"
            elif fps >= 1.3 * best_fps and fps >= best_fps + 0.2:
                best_fps, best_name = fps, name
                adopted.update(change)
                rec["decision"] = "ADOPTED (kept for later experiments)"
            else:
                rec["decision"] = "not better, reverted"
            rec["minutes"] = round((time.time() - t_start) / 60, 1)
            log(rec)
            if fps >= a.target:
                log({"note": f"target of {a.target} fps reached, stopping early"})
                break
    finally:
        if not a.dry_run:
            final = apply_settings(base_text, dict(BASELINE, **adopted))
            open(os.path.join(a.out, "best_camcheck.yaml"), "w", newline="\n", encoding="utf-8").write(final)
            open(work, "w", newline="\n", encoding="utf-8").write(final)
            if validate()[0]:
                fl, _, _ = ota()
                log({"final": "flashed best settings", "ok": fl, "adopted": adopted, "best": best_name, "best_fps": best_fps})
        if os.path.exists(work):
            os.remove(work)
        log({"done": True})


if __name__ == "__main__":
    main()

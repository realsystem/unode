import os
"""Build esphome/sim-gen.yaml from the real node config.

Differences from the real config (nothing else changes):
  * the pulse_counter 'vib_rate' becomes a template sensor replaying scenarios.SEGMENTS
  * a 'Sim time' sensor publishes seconds since boot every second (for aligning logs)
  * MQTT discovery off (no stray HA entities), run-hours counter not restored from flash
Usage: python make_sim_yaml.py <real.yaml> <out.yaml> [filters_yaml_file]
  filters_yaml_file: optional text that replaces the real 'Generator running' block (for A/B tests)
"""
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scenarios import PERIOD, SEGMENTS, UPDATE

real, out = sys.argv[1], sys.argv[2]
override = open(sys.argv[3]).read() if len(sys.argv) > 3 else None
text = open(real).read()

starts = ", ".join(f"{s}.0f" for s, _ in SEGMENTS)
rates = ", ".join(f"{r}.0f" for _, r in SEGMENTS)
n = len(SEGMENTS)
sim_sensor = f"""  - platform: template
    id: vib_rate
    name: "Vibration pulses per minute"
    unit_of_measurement: "pulses/min"
    update_interval: 10s
    lambda: |-
      static const float seg_start[] = {{{starts}}};
      static const float seg_rate[] = {{{rates}}};
      const int N = {n};
      const double P = {PERIOD}.0;
      const double t1 = millis() / 1000.0, t0 = t1 - {UPDATE};
      double total = 0.0;
      for (int k = (int) floor(t0 / P); k <= (int) floor(t1 / P); k++) {{
        for (int i = 0; i < N; i++) {{
          double e = (i + 1 < N) ? seg_start[i + 1] : P;
          double a = fmax(t0, k * P + seg_start[i]), b = fmin(t1, k * P + e);
          if (b > a) total += seg_rate[i] * (b - a);
        }}
      }}
      return total / {UPDATE};

  - platform: template
    name: "Sim time"
    update_interval: 1s
    accuracy_decimals: 0
    lambda: |-
      return millis() / 1000.0;
"""

# 1. replace the pulse_counter sensor block
pat = re.compile(r"  - platform: pulse_counter\n(?:    .*\n|\n(?=    ))+", re.M)
m = pat.search(text)
assert m, "pulse_counter block not found"
text = text[:m.start()] + sim_sensor + "\n" + text[m.end():]

# GPIO13 has a single user in the sim, so the sharing flag would be rejected
text = text.replace("      allow_other_uses: true\n", "")

# 2. quiet side effects
assert "  discovery: true" in text
text = text.replace("  discovery: true", "  discovery: false")
text = text.replace("    restore_value: true\n    initial_value: \"0\"\n", "    restore_value: false\n    initial_value: \"0\"\n", 1)

# 3. optional override of the Generator running block
if override:
    pat2 = re.compile(r"  - platform: template\n    id: gen_running\n(?:    .*\n|\n(?=    ))+", re.M)
    m2 = pat2.search(text)
    assert m2, "gen_running block not found"
    text = text[:m2.start()] + override.rstrip("\n") + "\n\n" + text[m2.end():]

open(out, "w", newline="\n").write(text)
print("wrote", out)

import os
"""Score an observed run against the expected behaviour and against the model.

Usage: python score.py <log> <design: A|B|C>
Parses the observer log (wall_time <tab> topic <tab> payload), aligns transitions with the
node's 'Sim time', and checks the first scenario period.
"""
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import *
from scenarios import *

log, design = sys.argv[1], sys.argv[2]
sim_t = None
events = []
for line in open(log):
    wall, topic, payload = line.rstrip("\n").split("\t")
    if topic.endswith("sensor/sim_time/state"):
        sim_t = float(payload)
    elif topic.endswith("binary_sensor/generator_running/state"):
        events.append((sim_t, payload == "ON"))

# Only the first period; drop duplicates of the same state
obs, last = [], None
for t, v in events:
    if t is None or t > PERIOD:
        continue
    if last is None:        # first publish after boot, not a transition
        last = v
        if v:
            obs.append((t, v))
        continue
    if v != last:
        obs.append((t, v)); last = v

specs = {"A": [("on", 20), ("off", 60)], "B": [("off", 60), ("on", 20)]}
d = LambdaDesign("C", 20, 60) if design == "C" else FilterDesign(design, specs[design])
model = [(t, v) for t, v in run(d, window_rate, PERIOD, first=UPDATE)]
# the model's boot-time OFF publish is not a transition worth comparing
model = [e for e in model if not (e[1] is False and e[0] <= 61)]

print("observed :", obs)
print("model    :", model)

# Expected behaviour (what a correct design does)
expect = [(130, True), (390, False), (610, True), (720, False)]
ok = True
for (et, ev) in expect:
    hit = [t for t, v in obs if v == ev and abs(t - et) <= 8]
    good = bool(hit); ok &= good
    print(f"  expect {'ON ' if ev else 'OFF'} near {et:>3}s : {'ok   ' + str(hit[0]) if good else 'MISSING'}")
extra = [(t, v) for t, v in obs if not any(v == ev and abs(t - et) <= 8 for et, ev in expect)]
print("  unexpected transitions:", extra if extra else "none")
print("RESULT:", "PASS" if ok and not extra else "FAIL")

import os
"""Check the model against the two traces recorded on the real board."""
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import *

# pulse_counter reported at 8,18,28,... s (test-relative) in both runs.
trace_old = {8: 4230, 18: 6444, 28: 5952, 38: 2358, 98: 618, 108: 4746, 118: 6096, 128: 3864}
trace_swap = {8: 3216, 18: 6396, 28: 6984, 38: 3174, 78: 4986, 88: 7602, 98: 7482, 108: 6426,
              118: 6414, 128: 7086, 138: 6186, 148: 5135, 158: 6426, 168: 6660, 178: 5610}


def mk(tr):
    return lambda t: tr.get(int(round(t)), 0)


cases = [
    ("old order (on,off)", [("on", 20), ("off", 60)], trace_old,
     "real: on@28  off@108  on@119"),
    ("swapped (off,on)", [("off", 60), ("on", 20)], trace_swap,
     "real: stayed off for 180 s"),
]
for name, specs, tr, real in cases:
    ev = run(FilterDesign(name, specs), mk(tr), 180, first=8)
    print(f"{name:20s} model: {ev}")
    print(f"{'':20s} {real}")

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import *
from scenarios import *

T = 2 * PERIOD  # shows the second period too (steady state, after boot)
designs = [
    FilterDesign("A original  on20,off60", [("on", 20), ("off", 60)]),
    FilterDesign("B swapped   off60,on20", [("off", 60), ("on", 20)]),
    LambdaDesign("C lambda    on20,off60", 20, 60),
    LambdaDesign("C2 lambda   on30,off90", 30, 90),
]
exp = [  # (window start, window end, expected)  expected state must hold through the window
    (0, 100, False, "idle + 12 s bump: stays OFF"),
    (150, 600 - 0, None, ""),
]
for d in designs:
    ev = run(d, window_rate, T, first=UPDATE)
    print(f"\n{d.name}")
    print("  events (s, state):", [e for e in ev if e[0] < T - 5])

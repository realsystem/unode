"""Scripted vibration scenario shared by the Python model and the on-device simulator.

SEGMENTS are (start_s, pulses_per_min). The pulse_counter reports, every 10 s, the average
rate over the previous 10 s window. The scenario repeats every PERIOD seconds.
Edges sit 3 s off the 10 s update grid on purpose.

Expected behaviour of a correct "Generator running":
  0-103   OFF   idle, then a 12 s bump (must not turn on)
  ~130    ON    after 80 s of sustained vibration (on-delay)
  183-248 stays ON through a 65 s dropout (about 50 s of silent readings, < 60 s hold)
  ~390    OFF   60 s after vibration stops at 313
  393-583 OFF   below-threshold rate and three 12 s bursts must not turn it on
  ~610    ON    sustained again
  ~720    OFF   60 s after it stops at 643
"""
PERIOD = 760
SEGMENTS = [
    (0, 0),
    (43, 3000), (55, 0),       # 12 s bump
    (103, 3000), (183, 0),     # sustained run
    (248, 3000), (313, 0),     # resumes after a 65 s dropout, then stops
    (393, 4), (453, 0),        # 4 pulses/min: below run_threshold
    (463, 3000), (475, 0),     # 12 s burst
    (503, 3000), (515, 0),     # 12 s burst
    (543, 3000), (555, 0),     # 12 s burst
    (583, 3000), (643, 0),     # sustained 60 s, then stops
]
UPDATE = 10.0


def window_rate(t):
    """Average rate over (t-10, t], with the scenario repeating every PERIOD."""
    t0, t1 = t - UPDATE, t
    total = 0.0
    for k in range(int(t0 // PERIOD), int(t1 // PERIOD) + 1):
        base = k * PERIOD
        for i, (s, r) in enumerate(SEGMENTS):
            e = SEGMENTS[i + 1][0] if i + 1 < len(SEGMENTS) else PERIOD
            a, b = max(t0, base + s), min(t1, base + e)
            if b > a:
                total += r * (b - a)
    return total / UPDATE

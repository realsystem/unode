"""Discrete-time model of the UNODE generator-running pipeline.

Mirrors ESPHome semantics read from esphome/components/binary_sensor/filter.cpp:
  * the template binary_sensor lambda runs every loop and publishes every time
  * every Filter de-duplicates its own input (Filter::input)
  * DelayedOn : true  -> (re)arm timer, emit nothing;   false -> cancel timer, emit false
  * DelayedOff: false -> (re)arm timer, emit nothing;   true  -> cancel timer, emit true
  * timers are keyed per filter instance (set_timeout replaces)
pulse_counter reports a new pulses/min value every 10 s.
"""
from dataclasses import dataclass, field

DT = 0.05
THR = 5.0


class Filter:
    def __init__(self):
        self.last = None
        self.timer = None  # absolute fire time
        self.next = None
        self.sink = None

    def output(self, v, now):
        if self.next:
            self.next.input(v, now)
        else:
            self.sink(v, now)

    def input(self, v, now):
        if self.last is not None and v == self.last:
            return
        self.last = v
        r = self.new_value(v, now)
        if r is not None:
            self.output(r, now)

    def tick(self, now):
        if self.timer is not None and now >= self.timer:
            self.timer = None
            self.fire(now)


class DelayedOn(Filter):
    def __init__(self, d):
        super().__init__(); self.d = d

    def new_value(self, v, now):
        if v:
            self.timer = now + self.d; self.pending = True
            return None
        self.timer = None
        return False

    def fire(self, now):
        self.output(True, now)


class DelayedOff(Filter):
    def __init__(self, d):
        super().__init__(); self.d = d

    def new_value(self, v, now):
        if not v:
            self.timer = now + self.d
            return None
        self.timer = None
        return True

    def fire(self, now):
        self.output(False, now)


def chain(filters, sink):
    for a, b in zip(filters, filters[1:]):
        a.next = b
    filters[-1].sink = sink
    return filters


class Design:
    """Base: raw -> state. Subclasses implement step(now, vib)."""
    name = "?"

    def __init__(self):
        self.state = None  # published (None = unknown)

    def pub(self, v, now):
        if v != self.state:
            self.state = v
            self.events.append((round(now, 2), v))


class FilterDesign(Design):
    def __init__(self, name, specs):
        super().__init__(); self.name = name; self.events = []
        self.filters = chain([DelayedOn(d) if k == "on" else DelayedOff(d) for k, d in specs], self.pub)

    def step(self, now, vib):
        raw = (vib is not None) and vib > THR  # NaN > thr is false
        self.filters[0].input(raw, now)
        for f in self.filters:
            f.tick(now)


class LambdaDesign(Design):
    """Hysteresis state machine in the template lambda: no filters."""

    def __init__(self, name, on_s=20.0, off_s=60.0):
        super().__init__(); self.name = name; self.events = []
        self.on_s, self.off_s = on_s, off_s
        self.act = False; self.since = 0.0; self.last_active = -1e9; self.running = False

    def step(self, now, vib):
        active = (vib is not None) and vib > THR
        if active:
            if not self.act:
                self.act = True; self.since = now
            self.last_active = now
        else:
            self.act = False
        if not self.running:
            if self.act and now - self.since >= self.on_s:
                self.running = True
        else:
            if (not self.act) and now - self.last_active >= self.off_s:
                self.running = False
        self.pub(self.running, now)


def run(design, rate_fn, t_end, update=10.0, first=None):
    now = 0.0; vib = None; next_upd = update if first is None else first
    while now < t_end:
        if now >= next_upd:
            vib = rate_fn(now); next_upd += update
        design.step(now, vib)
        now += DT
    return design.events


def timeline(segments):
    """segments: list of (start_s, rate). Returns rate_fn."""
    segs = sorted(segments)

    def f(t):
        r = 0.0
        for s, v in segs:
            if t >= s:
                r = v
        return r
    return f

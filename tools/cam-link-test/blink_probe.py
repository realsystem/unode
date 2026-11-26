"""Time a blinking light as the ESP32-CAM sees it.

Usage: python blink_probe.py <camera-ip> [seconds] [port]      (default 30 s, port 8080)
Needs: numpy, opencv-python-headless.
Reads the MJPEG stream, finds the green LEDs on its own (where green ever appears), takes the
three right-most as POWER, PUMP, MPPT (the test target is a phone on its side showing the RPS panel
animation, POWER at the right), and reports how long each light is lit and unlit.
The reading is the LED's "greenness" (G minus the larger of R and B) near its centre.
Neighbouring LEDs' glow bleeds into each other at small frame sizes, so look at each light's swing
(lit vs unlit mean), not at one fixed threshold.
"""
import re
import socket
import sys
import time

import cv2
import numpy as np

host = sys.argv[1]
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
port = int(sys.argv[3]) if len(sys.argv) > 3 else 8080
sock = socket.create_connection((host, port), timeout=5)
sock.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
sock.settimeout(2)
buf, frames, t0 = b"", [], time.time()
while time.time() - t0 < secs:
    try:
        c = sock.recv(65536)
    except socket.timeout:
        continue
    if not c:
        break
    buf += c
    while True:
        m = re.search(rb"Content-Length:\s*(\d+)\r\n\r\n", buf)
        if not m:
            break
        n = int(m.group(1))
        if len(buf) < m.end() + n:
            break
        frames.append((time.time() - t0, buf[m.end():m.end() + n]))
        buf = buf[m.end() + n:]
sock.close()
print(f"captured {len(frames)} frames in {secs:.0f}s -> {len(frames) / secs:.1f} fps")
if len(frames) < 10:
    sys.exit("too few frames to analyse; run measure_link.py first and check the camera")

imgs = [cv2.imdecode(np.frombuffer(d, np.uint8), cv2.IMREAD_COLOR).astype(np.float32) for _, d in frames]
T = np.array([t for t, _ in frames])


def greenness(im):
    b, g, r = im[..., 0], im[..., 1], im[..., 2]
    return g - np.maximum(r, b)


maxmap = np.max([greenness(i) for i in imgs], axis=0)
mask = (cv2.GaussianBlur(maxmap, (0, 0), 1.0) > 20).astype(np.uint8)
n, lab, stats, cent = cv2.connectedComponentsWithStats(mask)
blobs = sorted([(cent[i][0], cent[i][1], stats[i][cv2.CC_STAT_AREA]) for i in range(1, n) if stats[i][cv2.CC_STAT_AREA] >= 3],
               key=lambda b: -b[0])
if len(blobs) < 3 and blobs:
    # the glows merged into one blob: split the biggest one into separate peaks along its row
    big = max(blobs, key=lambda b: b[2])
    cy = int(round(big[1]))
    band = maxmap[max(0, cy - 4):cy + 5, :].max(axis=0)
    band = cv2.GaussianBlur(band.reshape(1, -1), (0, 0), 1.2).ravel()
    thr = 0.55 * band.max()
    peaks = [x for x in range(2, len(band) - 2)
             if band[x] >= thr and band[x] >= band[x - 1] and band[x] > band[x + 1] and band[x] >= band[x - 2] and band[x] > band[x + 2]]
    kept = []
    for x in sorted(peaks, reverse=True):
        if all(abs(x - k) >= 8 for k in kept):
            kept.append(x)
    blobs = [(float(x), float(cy), 1) for x in kept]
if len(blobs) < 3:
    sys.exit("could not find three LEDs; is the phone showing the pumping animation, and in view?")
NAMES = ["POWER", "PUMP", "MPPT"]
pts = blobs[:3]
G = np.array([[float(greenness(im)[max(0, int(y) - 3):int(y) + 4, max(0, int(x) - 3):int(x) + 4].max()) for x, y, _ in pts]
              for im in imgs])
lit = G > 20
print("\nLED     lit%   transitions   mean greenness lit / unlit")
for i, name in enumerate(NAMES):
    s = lit[:, i]
    lit_mean = G[s, i].mean() if s.any() else float("nan")
    unlit_mean = G[~s, i].mean() if (~s).any() else float("nan")
    print(f"{name:6s} {100 * s.mean():4.0f}%   {int(np.sum(np.diff(s.astype(int)) != 0)):4d}          {lit_mean:6.1f} / {unlit_mean:6.1f}")

s = lit[:, 2].astype(int)
runs_on, runs_off = [], []
cur, start = s[0], T[0]
for k in range(1, len(s)):
    if s[k] != cur:
        (runs_on if cur else runs_off).append(T[k] - start)
        cur, start = s[k], T[k]
on, off = runs_on[1:], runs_off[1:]                 # drop the partial first runs
if len(on) >= 3 and len(off) >= 3:
    print(f"\nMPPT as seen by the camera: on-run median {np.median(on):.2f}s (n={len(on)}), "
          f"off-run median {np.median(off):.2f}s (n={len(off)}), cycle {np.median(on) + np.median(off):.2f}s")
else:
    print(f"\nnot enough complete MPPT cycles (on runs {len(on)}, off runs {len(off)})")

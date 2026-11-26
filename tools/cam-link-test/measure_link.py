"""Measure the link to a running ESP32-CAM: ping loss/latency and MJPEG stream speed.

Usage: python measure_link.py <camera-ip> [stream-seconds] [runs]
Standard library only. The stream is read from port 8080 (the ESPHome camera web server in
`stream` mode). The snapshot port (8081) is NOT used: it is slow because ESPHome's camera only
captures fast while a stream is requested.
"""
import json
import re
import socket
import statistics
import subprocess
import sys
import time


def ping(host, n=30):
    """Windows `ping`. Returns loss % and latency of the replies."""
    r = subprocess.run(["ping", "-n", str(n), "-w", "2000", host], capture_output=True, text=True)
    times = [int(x) for x in re.findall(r"time[=<](\d+)ms", r.stdout)]
    return {"replies": len(times), "of": n, "loss_pct": round(100 * (n - len(times)) / n, 1),
            "median_ms": statistics.median(times) if times else None, "max_ms": max(times) if times else None}


def stream(host, secs=20, port=8080):
    """Read the MJPEG stream for `secs` seconds. Returns frames/s and kB/s."""
    frames, nbytes = 0, 0
    try:
        s = socket.create_connection((host, port), timeout=5)
    except OSError:
        return {"fps": 0.0, "kBps": 0.0, "frames": 0}
    s.sendall(f"GET / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
    s.settimeout(2)
    buf = b""
    t0 = time.time()
    while time.time() - t0 < secs:
        try:
            c = s.recv(65536)
        except socket.timeout:
            continue
        if not c:
            break
        buf += c
        while True:                                    # parts carry a Content-Length header
            m = re.search(rb"Content-Length:\s*(\d+)\r\n\r\n", buf)
            if not m:
                break
            n = int(m.group(1))
            if len(buf) < m.end() + n:
                break
            buf = buf[m.end() + n:]
            frames += 1
            nbytes += n
    s.close()
    el = time.time() - t0
    return {"fps": round(frames / el, 2), "kBps": round(nbytes / el / 1024, 1), "frames": frames}


def measure(host, secs=20, runs=2, pause=25):
    """Ping, then `runs` stream runs. The camera needs `pause` seconds to release the stream socket
    between runs (opening a new stream too early, or leaving one half-open, stalls it)."""
    p = ping(host)
    results = []
    for i in range(runs):
        results.append(stream(host, secs))
        if i < runs - 1:
            time.sleep(pause)
    return {"ping": p, "stream": results,
            "fps_mean": round(statistics.mean(r["fps"] for r in results), 2),
            "kBps_mean": round(statistics.mean(r["kBps"] for r in results), 1)}


if __name__ == "__main__":
    host = sys.argv[1]
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 20
    runs = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    print(json.dumps(measure(host, secs, runs), indent=2))

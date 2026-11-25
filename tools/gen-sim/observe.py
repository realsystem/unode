"""Record MQTT messages from the node and print the Generator-running transitions.

Usage: python observe.py <secrets.yaml> <seconds> <logfile>
Prints transitions as (sim_time_s, state) using the node's own 'Sim time' sensor.
"""
import re
import sys
import time

import paho.mqtt.client as mqtt

secrets_path, seconds, logfile = sys.argv[1], int(sys.argv[2]), sys.argv[3]
sec = dict(re.findall(r'^(\w+):\s*"(.*)"', open(secrets_path).read(), re.M))
T = "unode-gen-poc/"
log = open(logfile, "w")
sim_t = [None]
events, rates = [], []


def on_message(client, userdata, m):
    now = time.time()
    p = m.payload.decode("utf-8", "replace")
    log.write(f"{now:.2f}\t{m.topic}\t{p}\n"); log.flush()
    if m.topic == T + "sensor/sim_time/state":
        sim_t[0] = float(p)
    elif m.topic == T + "binary_sensor/generator_running/state":
        events.append((sim_t[0], p))
        print(f"  generator_running -> {p}   at sim t={sim_t[0]}", flush=True)
    elif m.topic == T + "sensor/vibration_pulses_per_minute/state":
        rates.append((sim_t[0], float(p)))


c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="claude-observer")
c.username_pw_set(sec["mqtt_user"], sec["mqtt_password"])
c.on_message = on_message
c.connect(sec["mqtt_broker"], 1883, 15)
c.subscribe(T + "#")
c.loop_start()
print(f"observing {seconds}s ...", flush=True)
time.sleep(seconds)
c.loop_stop()
print("events:", events)
print("rate readings:", [(t, round(v)) for t, v in rates])

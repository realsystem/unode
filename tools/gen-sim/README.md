# gen-sim: "Generator running" simulator

Tests the vibration-to-"Generator running" logic of `esphome/unode-gen-poc.yaml` without a
generator. Two parts that cross-check each other:

1. **Python model** (`model.py`, `scenarios.py`, `compare.py`): fast, runs anywhere.
2. **On-device replay**: `make_sim_yaml.py` copies the real node config and swaps the
   `pulse_counter` for a template sensor that replays the same scripted vibration scenario
   (`scenarios.py`). The real filter/lambda logic then runs on the real ESP8266, and
   `observe.py` + `score.py` record and grade the MQTT output.

The scenario (760 s, repeating) covers: a 12 s bump (must not turn on), a sustained run, a 65 s
dropout (must stay on), a stop (off after 60 s), a 4/min signal below `run_threshold`, three
12 s bursts (must stay off), a second sustained run and stop.

## Run it
```
python tools/gen-sim/compare.py                         # model only, all designs
python tools/gen-sim/make_sim_yaml.py esphome/unode-gen-poc.yaml esphome/sim-gen.yaml
cd esphome && python -m esphome run sim-gen.yaml --device COM3 --no-logs
python ../tools/gen-sim/observe.py secrets.yaml 790 run.log   # while it replays
python ../tools/gen-sim/score.py run.log C                    # C = lambda design, A/B = filters
```
Pass `block_A.yaml` / `block_B.yaml` as a third argument to `make_sim_yaml.py` to replay the
old filter-based designs instead.

The sim config turns MQTT discovery off and does not restore run hours from flash, so it does not
add entities to Home Assistant or change the stored run time. It still publishes to the node's
normal state topics, so Home Assistant will show the simulated "Generator running" and vibration
values while it runs. Delete `esphome/sim-gen.yaml` and reflash the real config afterwards.

## Caveat
The model matches the on-device result for the lambda design (all four transitions within 1 s)
but not for the filter designs (A/B): on the board they turned on earlier and glitched more than
the model predicts. Treat the model as a check on the lambda design, and use the on-device run as
the ground truth for anything involving `delayed_on` / `delayed_off`.

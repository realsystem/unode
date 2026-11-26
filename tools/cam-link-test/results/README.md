# Bench results: ESP32-CAM Wi-Fi link test

One board (AI-Thinker ESP32-CAM, OV2640), one router, one scene (a phone showing the RPS panel
animation), powered from a USB-serial adapter. All numbers are as measured; short runs, so treat
them as evidence, not as specifications. Summary and conclusions: `docs/vision-addon.md`
("ESP32-CAM on a weak Wi-Fi link"). How to repeat: `../README.md`.

## Files
| File | Content |
|---|---|
| `queue_run.jsonl` | The first queue (`run_experiments.py`, earlier version of the same logic): E0 baseline, E1a/E1b camera clock, E2a/E2b TX power, E3 frame size. Stopped early at the 5 frames/s target, so E4 (buffers) was not run. One JSON line per experiment. |
| `aba_repeat.jsonl` | The repeat test: tuned build (A1), original build (B), tuned build again (A2), each freshly flashed over the air. Per round: frames/s, kB/s, ping loss, median and worst ping. |

## Queue run: frames per second (mean of two 20 s stream runs)
| Experiment | Frames/s | kB/s | Ping median / worst (ms) |
|---|---|---|---|
| E0 baseline: 20 MHz clock, 800x600 | 0.32 | 9.0 | 19.5 / 183 |
| E1a clock 10 MHz | 0.05 | 1.3 | 84.5 / 620 |
| E1b clock 8 MHz | 4.6 | 122.5 | 8.5 / 59 |
| E2a TX power 20 dB (with 8 MHz) | 4.57 | 119.6 | 7.5 / 15 |
| E2b TX power 15 dB (with 8 MHz) | 4.74 | 123.0 | 7.0 / 30 |
| E3 320x240 q25 (with 8 MHz) | 8.59 | 38.8 | 10 / 30 |

Ping loss was 0 % in every measurement of this queue. Earlier, before the queue, the original build showed
3-10 % loss, a 115-215 ms median ping and a 220 s over-the-air update.

## Repeat test (A/B/A): frames per second, each round = 30 pings + two 20 s stream runs
| Phase | Round 1 | Round 2 | Round 3 | Mean | Ping median / worst (ms) | Loss |
|---|---|---|---|---|---|---|
| A1 tuned (8 MHz, 320x240) | 8.59 | 8.62 | 8.19 | 8.47 | 7-8 / 13-21 | 0 % |
| B original (20 MHz, 800x600) | 1.17 | 1.18 | | 1.17 | 12-15 / 37-109 | 0 % |
| A2 tuned again | 8.59 | 8.62 | 8.04 | 8.42 | 7-8.5 / 15-31 | 0 % |

The original build's speed varies from test to test (0.05-0.5 frames/s earlier, 0.32 in the queue,
1.17 here) but was always below the 4 frames/s a blink needs. The tuned build stayed between 8.04 and
8.62 frames/s in all six rounds, across two fresh flashes (reboots).

## Blink timing as seen by the camera (phone animation: 1.00 s on / 1.20 s off, cycle 2.20 s)
| Run | MPPT on-run median | off-run median | Cycle | Complete cycles |
|---|---|---|---|---|
| 1 (first successful run, 30 s) | 0.99 s | 1.19 s | 2.18 s | 13 |
| 2 (`blink_probe.py` from the repo, 25 s) | 1.03 s | 1.17 s | 2.20 s | 10-11 |
| 3 | 0.94 s | 1.21 s | 2.15 s | 13 |
| 4 | 1.03 s | 1.18 s | 2.21 s | 12-13 |
| 5 | 1.02 s | 1.18 s | 2.21 s | 12-13 |

In runs 2-5 POWER and PUMP read steady (lit 100 % of frames, no transitions). In an earlier run, with
the phone in a slightly different position, POWER showed spurious transitions from the neighbouring
glow (its reading moved between about 19 and 27), which is why steady versus blinking should be decided
from how much a light's reading swings, not from one fixed threshold.

These runs check the camera, the settings and the timing method against a known animation. They do not
measure the real RPS controller.

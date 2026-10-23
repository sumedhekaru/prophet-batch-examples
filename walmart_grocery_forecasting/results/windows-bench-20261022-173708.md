# Benchmark: local-bench-20261022-173708

1,437 items · default × 3, events × 3, events_snap × 3 runs · 12th Gen Intel(R) Core(TM) i7-1260P (16 logical CPUs, 16 available) · Windows-10-10.0.19045-SP0 · Python 3.12.10 · prophet 1.5.0 · prophet-batch 0.1.2 (PyPI) · examples 6d2f22b

## Speed: seconds for all items (fit + forecast), median (min–max) over repetitions

### default `Prophet()` (16 workers)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock, serial¹ | 1 | 1,047.6 (869.9–1,104.7) | 583.0 (490.9–624.7) | 1,630.5 (1,360.9–1,729.5) | 0.3 (0.2–0.3)× |
| stock, process pool | 16 | 283.3 (247.5–332.8) | 114.1 (109.8–121.4) | 397.4 (357.3–454.2) | 1.0 (1.0–1.0)× |
| prophet-batch, sampled history intervals | 1 | 34.3 (32.9–41.0) | 360.5 (337.5–412.2) | 393.5 (371.8–453.2) | 1.0 (1.0–1.0)× |
| prophet-batch, analytic history intervals | 1 | 34.3 (32.9–41.0) | 38.1 (35.2–41.8) | 71.0 (69.5–82.7) | 5.5 (5.1–5.6)× |
| prophet-batch, sampled history intervals | 16 | 16.6 (16.4–23.3) | 84.7 (84.4–93.0) | 101.1 (101.0–116.3) | 3.9 (3.5–3.9)× |
| prophet-batch, analytic history intervals | 16 | 16.6 (16.4–23.3) | 18.2 (17.5–20.7) | 34.6 (34.1–43.9) | 10.3 (10.3–11.6)× |
| forecast_many (one step), sampled history intervals² | 16 | 88.6 (86.3–102.8) | 0.0 (0.0–0.0) | 88.6 (86.3–102.8) | 4.4 (4.1–4.5)× |
| forecast_many (one step), analytic history intervals² | 16 | 23.4 (23.0–28.7) | 0.0 (0.0–0.0) | 23.4 (23.0–28.7) | 15.8 (15.5–17.0)× |

### + M5 events as holidays (16 workers)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock, serial¹ | 1 | 1,110.6 (1,071.8–1,415.7) | 561.7 (550.1–683.7) | 1,660.7 (1,633.4–2,099.5) | 0.3 (0.2–0.3)× |
| stock, process pool | 16 | 329.3 (326.1–345.7) | 135.2 (134.6–138.7) | 464.5 (460.6–484.4) | 1.0 (1.0–1.0)× |
| prophet-batch, sampled history intervals | 1 | 40.6 (40.3–52.9) | 373.0 (367.1–405.1) | 413.6 (407.5–458.1) | 1.1 (1.1–1.1)× |
| prophet-batch, analytic history intervals | 1 | 40.6 (40.3–52.9) | 51.3 (51.2–55.6) | 95.9 (91.8–104.3) | 4.8 (4.6–5.0)× |
| prophet-batch, sampled history intervals | 16 | 21.1 (20.3–21.9) | 88.7 (86.7–91.6) | 109.0 (108.6–112.8) | 4.3 (4.2–4.3)× |
| prophet-batch, analytic history intervals | 16 | 21.1 (20.3–21.9) | 23.6 (22.2–25.8) | 44.2 (43.9–46.9) | 10.4 (10.3–10.6)× |
| forecast_many (one step), sampled history intervals² | 16 | 98.3 (96.1–98.7) | 0.0 (0.0–0.0) | 98.3 (96.1–98.7) | 4.8 (4.7–4.9)× |
| forecast_many (one step), analytic history intervals² | 16 | 34.8 (31.4–37.5) | 0.0 (0.0–0.0) | 34.8 (31.4–37.5) | 13.2 (12.4–15.4)× |

### + events + SNAP regressors (16 workers)

| method | workers | fit s | forecast s | total s | vs stock pool |
|---|---:|---:|---:|---:|---:|
| stock, serial¹ | 1 | 1,246.8 (1,135.2–1,467.9) | 591.2 (547.2–681.7) | 1,838.0 (1,682.5–2,149.7) | 0.3 (0.2–0.3)× |
| stock, process pool | 16 | 366.2 (360.8–387.7) | 142.5 (141.2–147.2) | 508.6 (502.0–534.9) | 1.0 (1.0–1.0)× |
| prophet-batch, sampled history intervals | 1 | 57.3 (51.0–61.8) | 373.2 (373.0–427.5) | 430.3 (424.2–489.3) | 1.2 (1.1–1.2)× |
| prophet-batch, analytic history intervals | 1 | 57.3 (51.0–61.8) | 60.4 (60.0–78.0) | 117.4 (111.4–139.8) | 4.3 (3.8–4.5)× |
| prophet-batch, sampled history intervals | 16 | 24.9 (24.4–31.8) | 94.7 (93.3–121.9) | 119.6 (117.8–153.7) | 4.2 (3.5–4.3)× |
| prophet-batch, analytic history intervals | 16 | 24.9 (24.4–31.8) | 28.7 (25.5–43.2) | 53.1 (50.4–75.0) | 9.6 (7.1–10.0)× |
| forecast_many (one step), sampled history intervals² | 16 | 105.2 (102.5–130.4) | 0.0 (0.0–0.0) | 105.2 (102.5–130.4) | 4.8 (4.1–4.9)× |
| forecast_many (one step), analytic history intervals² | 16 | 39.8 (39.6–59.1) | 0.0 (0.0–0.0) | 39.8 (39.6–59.1) | 12.6 (9.0–12.8)× |

² fit_many + predict_many in one call: the whole time is shown as fit, forecast as 0.

¹ Timed on a sample (30 items), extrapolated. With different worker counts by repetition, the workers column shows the first repetition's.

## Accuracy on the 28 held-out days (first repetition)

| model | method | WAPE | sMAPE | MASE | Δ MASE vs stock (± 2 SE) | 80% coverage |
|---|---|---:|---:|---:|---:|---:|
| default | stock, process pool | 0.3452 | 48.46 | 1.4282 | – | 0.721 |
| default | prophet-batch, sampled history intervals | 0.3438 | 48.39 | 1.4261 | -0.0021 ± 0.0023 | 0.719 |
| default | prophet-batch, analytic history intervals | 0.3438 | 48.39 | 1.4261 | -0.0021 ± 0.0023 | 0.720 |
| default | forecast_many (one step), sampled history intervals² | 0.3438 | 48.39 | 1.4261 | -0.0021 ± 0.0023 | 0.719 |
| default | forecast_many (one step), analytic history intervals² | 0.3438 | 48.39 | 1.4261 | -0.0021 ± 0.0023 | 0.720 |
| events | stock, process pool | 0.3478 | 48.91 | 1.4389 | – | 0.711 |
| events | prophet-batch, sampled history intervals | 0.3470 | 48.87 | 1.4377 | -0.0012 ± 0.0023 | 0.710 |
| events | prophet-batch, analytic history intervals | 0.3470 | 48.87 | 1.4377 | -0.0012 ± 0.0023 | 0.710 |
| events | forecast_many (one step), sampled history intervals² | 0.3470 | 48.87 | 1.4377 | -0.0012 ± 0.0023 | 0.710 |
| events | forecast_many (one step), analytic history intervals² | 0.3470 | 48.87 | 1.4377 | -0.0012 ± 0.0023 | 0.710 |
| events_snap | stock, process pool | 0.3422 | 48.53 | 1.4245 | – | 0.710 |
| events_snap | prophet-batch, sampled history intervals | 0.3415 | 48.46 | 1.4228 | -0.0017 ± 0.0021 | 0.708 |
| events_snap | prophet-batch, analytic history intervals | 0.3415 | 48.46 | 1.4228 | -0.0017 ± 0.0021 | 0.709 |
| events_snap | forecast_many (one step), sampled history intervals² | 0.3415 | 48.46 | 1.4228 | -0.0017 ± 0.0021 | 0.708 |
| events_snap | forecast_many (one step), analytic history intervals² | 0.3415 | 48.46 | 1.4228 | -0.0017 ± 0.0021 | 0.709 |

## Memory per step (main process: working set; workers: not measured on this platform)

| group | step | main process peak GB | largest worker GB | all workers GB |
|---|---|---:|---:|---:|
| default | stock_serial | 0.29 (0.29–0.29) | – | – |
| default | stock_pool | 0.24 (0.23–0.24) | – | – |
| default | batch n_jobs=1 | 0.75 (0.75–0.76) | – | – |
| default | batch n_jobs=16 | 0.66 (0.66–0.67) | – | – |
| default | forecast_many n_jobs=16 | 0.61 (0.61–0.62) | – | – |
| events | stock_serial | 0.29 (0.29–0.29) | – | – |
| events | stock_pool | 0.24 (0.24–0.24) | – | – |
| events | batch n_jobs=1 | 0.78 (0.78–0.79) | – | – |
| events | batch n_jobs=16 | 0.70 (0.69–0.70) | – | – |
| events | forecast_many n_jobs=16 | 0.62 (0.62–0.63) | – | – |
| events_snap | stock_serial | 0.36 (0.36–0.36) | – | – |
| events_snap | stock_pool | 0.31 (0.31–0.31) | – | – |
| events_snap | batch n_jobs=1 | 1.02 (1.02–1.03) | – | – |
| events_snap | batch n_jobs=16 | 0.96 (0.96–0.96) | – | – |
| events_snap | forecast_many n_jobs=16 | 0.85 (0.85–0.86) | – | – |

Median (min–max) over repetitions.

## Checks

- default: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events_snap: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.

# Docker: Linux (arm64) container on the same Mac

2026-10-22 · Debian 12 container (python:3.12-slim-bookworm) under Docker Desktop on the Apple M4, 10 CPUs and 13.7 GiB for the VM · Python 3.12.15 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** (image built from examples `c15f2d6`) · 1,437 items · 10 worker processes · **3 repetitions**, median (min–max). Reproduce: `sh walmart_grocery_forecasting/envs/docker/build.sh && REPS=3 sh walmart_grocery_forecasting/envs/docker/run.sh`. Every table: [docker-bench-20261022-225804.md](docker-bench-20261022-225804.md).

Same task as [the macOS run](local-macos-m4.md). Earlier results: [0.1.1](history/docker-linux-arm64-0.1.1.md), [pre-release](history/docker-linux-arm64-prerelease.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic | `fit_many` + `predict_many`, sampled |
|---|---:|---:|---:|---:|---:|
| default `Prophet()` | 59.2 | **5.0 (11.5×, 10.4–11.9)** | 16.9 (3.4×) | 6.7 (8.6×) | 18.8 (3.1×) |
| + M5 events as holidays | 76.5 | **6.7 (11.4×, 11.3–11.5)** | 18.7 (4.1×) | 8.8 (8.7×) | 21.4 (3.6×) |
| + events + SNAP regressors | 83.6 | **8.2 (10.2×, 9.8–10.2)** | 20.4 (4.1×) | 11.4 (7.3×) | 22.6 (3.6×) |

Speed-ups (×) are against the stock process pool of the same run, as median (min–max) over the 3 repetitions. `forecast_many` fits and forecasts each series in the same worker (one call); `fit_many` + `predict_many` returns the fitted models first. Serial stock and prophet-batch with one worker: in the full tables.

## Accuracy on the 28 held-out days (first repetition)

| model | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| default | 0.3450 / 0.3438 | 48.48 / 48.39 | 1.4277 / 1.4261 | −0.0015 ± 0.0023 | 0.722 / 0.720 |
| events | 0.3480 / 0.3470 | 48.94 / 48.87 | 1.4396 / 1.4377 | −0.0019 ± 0.0023 | 0.712 / 0.710 |
| events + SNAP | 0.3421 / 0.3415 | 48.54 / 48.46 | 1.4239 / 1.4228 | −0.0012 ± 0.0022 | 0.710 / 0.709 |

Every Δ MASE is within noise (prophet-batch is slightly lower in all three). prophet-batch's intervals are a little narrower: its fits reach the exact optimum, where Stan's L-BFGS stops short.

## Checks (every run)

- default: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events_snap: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.

"bit-identical" covers both checks: prophet-batch with one worker vs many, and `forecast_many` vs `fit_many` + `predict_many` (every forecast and fit, bit for bit).

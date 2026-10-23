# Windows laptop: Intel i7-1260P (16 threads)

2026-10-22 · Windows 10 22H2 (19045) · 12th Gen Intel Core i7-1260P (4 performance + 8 efficiency cores, 16 threads), 34 GB RAM, on mains power, High performance plan · Python 3.12.10 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** · examples `6d2f22b` · 1,437 items · 16 worker processes · **3 repetitions**, median (min–max). Run by the user on their own laptop (an everyday machine: other applications kept the CPU 23–53% busy, which slows both methods alike; speed-ups are within one run). Reproduce: `REPS=3 sh walmart_grocery_forecasting/envs/local/run.sh`. Every table: [windows-bench-20261022-173708.md](windows-bench-20261022-173708.md).

Same task as [the macOS run](local-macos-m4.md). Earlier results: [0.1.1](history/windows-i7-1260p-0.1.1.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic | `fit_many` + `predict_many`, sampled |
|---|---:|---:|---:|---:|---:|
| default `Prophet()` | 397.4 | **23.4 (15.8×, 15.5–17.0)** | 88.6 (4.4×) | 34.6 (10.3×) | 101.1 (3.9×) |
| + M5 events as holidays | 464.5 | **34.8 (13.2×, 12.4–15.4)** | 98.3 (4.8×) | 44.2 (10.4×) | 109.0 (4.3×) |
| + events + SNAP regressors | 508.6 | **39.8 (12.6×, 9.0–12.8)** | 105.2 (4.8×) | 53.1 (9.6×) | 119.6 (4.2×) |

Speed-ups (×) are against the stock process pool of the same run, as median (min–max) over the 3 repetitions. `forecast_many` fits and forecasts each series in the same worker (one call); `fit_many` + `predict_many` returns the fitted models first. Serial stock and prophet-batch with one worker: in the full tables.

## Accuracy on the 28 held-out days (first repetition)

| model | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| default | 0.3452 / 0.3438 | 48.46 / 48.39 | 1.4282 / 1.4261 | −0.0021 ± 0.0023 | 0.721 / 0.720 |
| events | 0.3478 / 0.3470 | 48.91 / 48.87 | 1.4389 / 1.4377 | −0.0012 ± 0.0023 | 0.711 / 0.710 |
| events + SNAP | 0.3422 / 0.3415 | 48.53 / 48.46 | 1.4245 / 1.4228 | −0.0017 ± 0.0021 | 0.710 / 0.709 |

Every Δ MASE is within noise (prophet-batch is slightly lower in all three). prophet-batch's intervals are a little narrower: its fits reach the exact optimum, where Stan's L-BFGS stops short.

## Checks (every run)

- default: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events_snap: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.

"bit-identical" covers both checks: prophet-batch with one worker vs many, and `forecast_many` vs `fit_many` + `predict_many` (every forecast and fit, bit for bit).

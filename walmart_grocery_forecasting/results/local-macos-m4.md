# Local run: macOS, Apple M4 (10 cores)

2026-10-22 · macOS 26.5.2 arm64 · Python 3.12.13 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** · examples `c15f2d6` · 1,437 M5 FOODS items, train 1,913 days, 28 days held out · 10 worker processes · **3 repetitions** of every model variant: median (min–max). Reproduce: `REPS=3 sh walmart_grocery_forecasting/envs/local/run.sh`. Every table, incl. memory per step: [local-bench-20261022-180148.md](local-bench-20261022-180148.md).

Every method fits the model and forecasts the history plus the 28 days, as `model.predict(model.make_future_dataframe(28))` does, keeping the interval columns. History intervals: sampled like stock (`history_uncertainty=True`, the default) or in exact closed form (`'analytic'`, one argument); future intervals are sampled either way. Linux container on the same Mac: [docker-linux-arm64.md](docker-linux-arm64.md). Earlier results: [0.1.1](history/local-macos-m4-0.1.1.md), [pre-release](history/local-macos-m4-prerelease.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic | `fit_many` + `predict_many`, sampled |
|---|---:|---:|---:|---:|---:|
| default `Prophet()` | 55.5 | **4.1 (13.6×, 12.2–14.4)** | 14.5 (3.9×) | 5.6 (9.9×) | 16.0 (3.5×) |
| + M5 events as holidays | 74.1 | **5.7 (13.1×, 13.1–14.0)** | 16.1 (4.6×) | 7.2 (10.5×) | 17.5 (4.3×) |
| + events + SNAP regressors | 79.5 | **6.9 (11.6×, 11.3–11.7)** | 17.3 (4.6×) | 9.2 (8.6×) | 19.5 (4.1×) |

Speed-ups (×) are against the stock process pool of the same run, as median (min–max) over the 3 repetitions. `forecast_many` fits and forecasts each series in the same worker (one call); `fit_many` + `predict_many` returns the fitted models first. Serial stock and prophet-batch with one worker: in the full tables.

## Accuracy on the 28 held-out days (first repetition)

| model | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| default | 0.3446 / 0.3438 | 48.43 / 48.39 | 1.4279 / 1.4261 | −0.0018 ± 0.0023 | 0.722 / 0.720 |
| events | 0.3479 / 0.3470 | 48.91 / 48.87 | 1.4388 / 1.4377 | −0.0011 ± 0.0021 | 0.712 / 0.710 |
| events + SNAP | 0.3423 / 0.3415 | 48.51 / 48.46 | 1.4238 / 1.4228 | −0.0010 ± 0.0022 | 0.710 / 0.709 |

Every Δ MASE is within noise (prophet-batch is slightly lower in all three). prophet-batch's intervals are a little narrower: its fits reach the exact optimum, where Stan's L-BFGS stops short.

## Checks (every run)

- default: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- events_snap: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.

"bit-identical" covers both checks: prophet-batch with one worker vs many, and `forecast_many` vs `fit_many` + `predict_many` (every forecast and fit, bit for bit).

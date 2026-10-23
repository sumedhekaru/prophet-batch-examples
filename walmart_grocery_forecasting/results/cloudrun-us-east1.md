# Cloud Run job: 4 vCPU, us-east1

2026-10-22 · Cloud Run job (us-east1), 4 vCPU / 8 GiB, one task, the [Docker image](../envs/docker/) built for linux/amd64 · Python 3.12.15 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** (image from examples `d5f2058`) · 1,437 items · **9 executions** (3 repetitions × 3 models), each on a fresh instance: median (min–max). Reproduce: `REPS=3 PROJECT=... REGION=... BUCKET=... sh walmart_grocery_forecasting/envs/cloudrun_job/deploy.sh`. Every table: [cloudrun-bench-20261022-181501.md](cloudrun-bench-20261022-181501.md).

**Workers.** A 4-vCPU job lands on one of two host shapes: 5 logical CPUs with a CPU quota of 4 (Intel Xeon 2.0 or 2.2 GHz; 6 of 9 executions) or 6 with a quota of 5 (AMD EPYC 7B13; the second repetition of each model); the pipeline and prophet-batch's `n_jobs=-1` follow the quota, so both methods run 4 (or 5) workers in the same execution, and every speed-up is within one execution. Earlier results: [0.1.1](history/cloudrun-us-east1-0.1.1.md), [pre-release](history/cloudrun-us-east1-prerelease.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic | `fit_many` + `predict_many`, sampled |
|---|---:|---:|---:|---:|---:|
| default `Prophet()` | 249.1 | **20.4 (13.0×, 12.2–13.2)** | 81.0 (3.2×) | 23.8 (10.7×) | 84.1 (3.1×) |
| + M5 events as holidays | 353.9 | **29.8 (12.0×, 11.8–12.5)** | 91.7 (3.9×) | 33.6 (10.7×) | 94.4 (3.8×) |
| + events + SNAP regressors | 381.0 | **35.6 (10.7×, 10.6–11.0)** | 97.0 (3.9×) | 42.7 (8.9×) | 102.7 (3.7×) |

Speed-ups (×) are against the stock process pool of the same run, as median (min–max) over the 3 repetitions. `forecast_many` fits and forecasts each series in the same worker (one call); `fit_many` + `predict_many` returns the fitted models first. Serial stock and prophet-batch with one worker: in the full tables.

## Accuracy on the 28 held-out days (first repetition)

| model | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| default | 0.3448 / 0.3438 | 48.47 / 48.39 | 1.4281 / 1.4261 | −0.0020 ± 0.0022 | 0.721 / 0.720 |
| events | 0.3483 / 0.3470 | 48.95 / 48.87 | 1.4401 / 1.4377 | −0.0024 ± 0.0022 | 0.711 / 0.710 |
| events + SNAP | 0.3420 / 0.3415 | 48.49 / 48.46 | 1.4233 / 1.4228 | −0.0006 ± 0.0021 | 0.710 / 0.709 |

Every Δ MASE is within noise (prophet-batch is slightly lower in all three). prophet-batch's intervals are a little narrower: its fits reach the exact optimum, where Stan's L-BFGS stops short.

## Checks (every run)

- default: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock max |Δ| 1.1e-13, prophet-batch max |Δ| 8.9e-10.
- events: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock max |Δ| 1.1e-13, prophet-batch max |Δ| 9.8e-10.
- events_snap: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock max |Δ| 1.1e-13, prophet-batch max |Δ| 2.6e-09.

"bit-identical" covers both checks: prophet-batch with one worker vs many, and `forecast_many` vs `fit_many` + `predict_many` (every forecast and fit, bit for bit).

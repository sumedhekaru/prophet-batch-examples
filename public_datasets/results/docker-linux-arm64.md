# Docker: Linux (arm64) container on the same Mac: six public datasets

2026-10-23 · Debian 12 container (python:3.12-slim-bookworm) under Docker Desktop on the Apple M4, 10 CPUs and 13.7 GiB
for the VM · Python 3.12.15 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** (image built from examples
`c15f2d6`) · 10 worker processes · the large datasets **3 times** each (one dataset per run), the small ones once.
Reproduce: `sh public_datasets/envs/docker/build.sh`, then `REPS=3 DATASETS=<dataset> sh public_datasets/envs/docker/run.sh`.
Every table: [M5 item × store](docker-bench-20261023-004920.md), [M4 Daily](docker-bench-20261022-233537.md),
[M5 item](docker-bench-20261023-002752.md), [small three](docker-bench-20261023-024627.md). Same task as
[the macOS run](macos-m4.md).

## Speed: fit + forecast of every series, against stock Prophet in a 10-process pool

| dataset | series | runs | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic |
|---|---:|---:|---:|---:|---:|---:|
| M4 Weekly | 359 | 1 | 14.6 s | **2.5 s (5.9×)** | 4.8 s (3.0×) | 4.5 s (3.2×) |
| M4 Hourly | 414 | 1 | 10.0 s | **2.9 s (3.5×)** | 4.3 s (2.3×) | 4.3 s (2.3×) |
| Tourism Monthly | 366 | 1 | 4.6 s | **2.1 s (2.2×)** | 2.6 s (1.8×) | 3.6 s (1.3×) |

| dataset | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|

## Accuracy on the held-out steps (first run of each dataset)

| M4 Daily | 0.1059 / 0.1052 | 11.68 / 11.61 | 11.9660 / 11.8888 | −0.0772 ± 0.0351 | 0.419 / 0.414 |
| M5 item | 0.3556 / 0.3546 | 54.39 / 54.33 | 1.3646 / 1.3626 | −0.0020 ± 0.0013 | 0.723 / 0.721 |
| M4 Weekly | 0.1306 / 0.1298 | 20.30 / 19.46 | 8.3001 / 8.1845 | −0.1156 ± 0.0594 | 0.554 / 0.550 |
| M4 Hourly | 0.0525 / 0.0548 | 18.07 / 18.20 | 1.6301 / 1.6357 | +0.0057 ± 0.0060 | 0.656 / 0.652 |
| Tourism Monthly | 0.1662 / 0.1699 | 26.86 / 27.00 | 2.2254 / 2.2310 | +0.0057 ± 0.0078 | 0.522 / 0.518 |

- M5 item × store: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- M4 Daily: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.

## Checks (every run)

- M4 Weekly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- M4 Hourly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- Tourism Monthly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.

## Memory: M5 item × store is close to Docker Desktop's limit

On Linux the run's main process keeps what earlier steps freed (its allocator does not hand it back to the system), so
on M5 item × store it reached **13.6 GB** in the `forecast_many` step (main process + workers 13.6 GB, against
14.7 GB for the whole Docker VM; macOS: 11.0 GB). All three repetitions finished, but with less memory they would not:
this is the comparison harness holding every method's results in one process, not `forecast_many` on its own. The
two-step path is the slowest to recover from it here (7.8×, against 11.0× on macOS).

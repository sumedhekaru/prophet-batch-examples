# Local run: macOS, Apple M4 (10 cores): six public datasets

2026-10-22 · macOS 26.5.2 arm64 · Python 3.12.13 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** · examples
`c15f2d6` · 10 worker processes · default `Prophet()` on each dataset's train split, forecasting the history plus
the held-out steps · the three large datasets **3 times** (median (min–max)), the three small ones once. Reproduce:
`REPS=3 sh public_datasets/envs/local/run.sh` and
`REPS=1 DATASETS="m4_weekly m4_hourly tourism_monthly" sh public_datasets/envs/local/run.sh`. Every table, incl.
memory per step and prophet-batch with one worker: [large](local-bench-20261022-183458.md),
[small](local-bench-20261022-211432.md).

## Speed: fit + forecast of every series, against stock Prophet in a 10-process pool

| dataset | series | runs | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic |
|---|---:|---:|---:|---:|---:|---:|
| M5 item × store | 30,490 | 3 | 992.9 s | **68.3 s (14.5×, 14.4–15.0)** | 281.5 s (3.6×) | 89.9 s (11.0×) |
| M4 Daily | 4,227 | 3 | 489.2 s | **13.2 s (37.1×, 36.8–37.1)** | 50.8 s (9.5×) | 16.2 s (30.2×) |
| M5 item | 3,049 | 3 | 109.0 s | **7.4 s (14.8×, 14.5–14.8)** | 28.6 s (3.8×) | 9.4 s (11.8×) |
| M4 Weekly | 359 | 1 | 13.0 s | **1.6 s (8.0×)** | 2.9 s (4.5×) | 2.6 s (5.1×) |
| M4 Hourly | 414 | 1 | 8.5 s | **2.1 s (4.0×)** | 3.2 s (2.6×) | 2.8 s (3.0×) |
| Tourism Monthly | 366 | 1 | 3.7 s | **1.4 s (2.7×)** | 1.7 s (2.2×) | 2.3 s (1.6×) |

Speed-ups (×) are against the stock pool of the same run. **`history_uncertainty='analytic'`** computes the history
intervals in exact closed form (the limit the sampled ones converge to); the default samples them like stock Prophet.
The gain grows with series length (M4 Daily: ≈ 2,400 days per series) and with the number of series; the small
datasets finish in seconds, where starting the worker processes takes about as long as the work. Scaling with the
number of series and with workers: [scaling-macos-m4.md](scaling-macos-m4.md).

## Accuracy on the held-out steps (first run of each dataset)

| dataset | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| M5 item × store | 0.7692 / 0.7687 | 143.11 / 143.09 | 1.6442 / 1.6428 | −0.0014 ± 0.0003 | 0.785 / 0.784 |
| M4 Daily | 0.1058 / 0.1052 | 11.66 / 11.61 | 11.9713 / 11.8888 | −0.0826 ± 0.0341 | 0.420 / 0.414 |
| M5 item | 0.3553 / 0.3546 | 54.38 / 54.33 | 1.3648 / 1.3626 | −0.0022 ± 0.0013 | 0.723 / 0.721 |
| M4 Weekly | 0.1308 / 0.1298 | 20.18 / 19.46 | 8.2945 / 8.1845 | −0.1100 ± 0.0514 | 0.554 / 0.550 |
| M4 Hourly | 0.0530 / 0.0548 | 18.08 / 18.20 | 1.6306 / 1.6357 | +0.0051 ± 0.0053 | 0.656 / 0.652 |
| Tourism Monthly | 0.1666 / 0.1699 | 26.83 / 27.00 | 2.2238 / 2.2310 | +0.0072 ± 0.0075 | 0.522 / 0.518 |

prophet-batch is more accurate beyond noise (± 2 SE) on four datasets and within noise on the other two.

## Fit quality

prophet-batch's log posterior (Prophet's own objective) is **at least Stan's on 38,905 of 38,905 series**; median gain
per dataset: M5 item × store 0.83, M4 Daily 3.5, M5 item 2.5, M4 Weekly 2.3, M4 Hourly 0.42, Tourism Monthly 0.98. No
series fell back to Stan.

## Checks (every run)

- M5 item × store: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- M4 Daily: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- M5 item: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock identical, prophet-batch identical.
- M4 Weekly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- M4 Hourly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- Tourism Monthly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.

"bit-identical" covers both checks: prophet-batch with one worker vs ten (all series, or a 2,000-series sample above
5,000 series), and `forecast_many` vs `fit_many` + `predict_many`.

## Memory

Each worker held ≈ 0.2–0.3 GB. The run's main process holds every method's results for comparison: on M5 item × store
it reached 10.6–11.0 GB (with 2.6 GB of workers at the same time). A user running `forecast_many` alone holds only the
frame it returns.

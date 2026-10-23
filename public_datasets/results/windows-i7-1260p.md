# Windows laptop: Intel i7-1260P (16 threads): the three small public datasets (partial)

2026-10-22 · Windows 10 22H2 · 12th Gen Intel Core i7-1260P, 16 threads, 34 GB RAM, mains power · Python 3.12.10 ·
prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** · examples `6d2f22b` · 16 worker processes · one run.
Run by the user on their everyday laptop (other applications kept the CPU 23–53% busy; speed-ups are within one run).
Reproduce: `REPS=1 DATASETS="m4_weekly m4_hourly tourism_monthly" sh public_datasets/envs/local/run.sh`. Every
table: [windows-bench-20261022-205229.md](windows-bench-20261022-205229.md).

**Partial:** the three large datasets were started (M5 item, M4 Daily) but stopped: the laptop went into connected
standby when its display turned off, which made one repetition's timings meaningless, and the laptop was needed. They
will be run again; the large-dataset results are on [macOS](macos-m4.md), [Linux](docker-linux-arm64.md),
[Cloud Run](cloudrun-us-east1.md) and [Dataproc](dataproc-us-east1.md).

## Speed: fit + forecast of every series, against stock Prophet in a 16-process pool

| dataset | series | runs | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic |
|---|---:|---:|---:|---:|---:|---:|
| M4 Weekly | 359 | 1 | 106.1 s | **16.0 s (6.6×)** | 26.2 s (4.0×) | 30.1 s (3.5×) |
| M4 Hourly | 414 | 1 | 68.3 s | **14.7 s (4.6×)** | 22.1 s (3.1×) | 23.8 s (2.9×) |
| Tourism Monthly | 366 | 1 | 44.1 s | **11.6 s (3.8×)** | 15.5 s (2.8×) | 19.9 s (2.2×) |

On Windows, starting worker processes costs more than on macOS or Linux, and these jobs are small (seconds of work):
here prophet-batch with one worker was faster than with 16 (`fit_many` + `predict_many`, analytic: 19.3 s vs 30.1 s
on M4 Weekly, 19.4 vs 23.8 s on M4 Hourly, 11.3 vs 19.9 s on Tourism Monthly). For small jobs on Windows, use fewer
workers.

## Accuracy on the held-out steps

| dataset | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| M4 Weekly | 0.1307 / 0.1298 | 20.35 / 19.46 | 8.2894 / 8.1845 | −0.1049 ± 0.0552 | 0.554 / 0.550 |
| M4 Hourly | 0.0529 / 0.0548 | 18.09 / 18.20 | 1.6309 / 1.6357 | +0.0048 ± 0.0055 | 0.655 / 0.652 |
| Tourism Monthly | 0.1657 / 0.1699 | 26.83 / 27.00 | 2.2230 / 2.2310 | +0.0080 ± 0.0075 | 0.522 / 0.518 |

M4 Weekly is more accurate beyond noise, M4 Hourly within noise; on Tourism Monthly prophet-batch is marginally less
accurate than stock here (+0.0080 against a ± 2 SE band of 0.0075; on macOS the same comparison was +0.0072 ± 0.0075,
within noise). The forecasts are the same as on the other platforms up to floating-point rounding; the stock side
differs slightly between platforms.

## Checks

- M4 Weekly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- M4 Hourly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.
- Tourism Monthly: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: one repetition.

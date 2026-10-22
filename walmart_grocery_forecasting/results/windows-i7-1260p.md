# Windows laptop: Intel Core i7-1260P (16 logical CPUs)

2026-10-22 · Windows 10 (10.0.19045) · Python 3.12.10 · prophet 1.5.0 and **prophet-batch 0.1.1, both from PyPI** ·
cmdstanpy 1.3.0 · pandas 3.0.6 · numpy 2.5.4 · examples `35862ae` · 1,437 M5 FOODS items, 28 days held out · 16
worker processes · **3 repetitions**: median (min–max). Reproduce: `REPS=3 sh
walmart_grocery_forecasting/envs/local/run.sh` (Git Bash). Every table:
[windows-bench-20261022-084539.md](windows-bench-20261022-084539.md).

Machine: on mains power, Windows' High performance power plan; other applications were open (CPU ≈ 17% at the
start), so the absolute times are a laptop in everyday use; the speed-ups vary less than the times.

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, serial¹ | stock, 16-process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|
| default `Prophet()` | 974.9 | 298.9 | 75.5 (4.0×) | **25.8 (11.6×, 11.6–11.9)** |
| + M5 events as holidays | 1,294.9 | 363.0 | 84.4 (4.5×) | **35.0 (11.2×, 10.4–12.2)** |
| + events + SNAP regressors | 1,347.6 | 393.7 | 93.7 (4.2×) | **43.5 (9.1×, 8.7–10.0)** |

¹ Timed on 30 items, extrapolated. Speed-ups are against the stock pool of the same run. Stock Prophet on Windows
pays ≈ 100 ms per model for a process cmdstanpy starts (`where.exe`); prophet-batch reuses one loaded Stan model per
process (0.1.1), so its speed-ups are in line with macOS (10.2× / 10.4× / 8.9×).

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | sMAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---|---:|---|
| default | 0.3452 / 0.3438 | 48.46 / 48.39 | 1.4282 / 1.4261 | −0.0021 ± 0.0023 | 0.721 / 0.720 |
| events | 0.3478 / 0.3470 | 48.91 / 48.87 | 1.4389 / 1.4377 | −0.0012 ± 0.0023 | 0.711 / 0.710 |
| events + SNAP | 0.3422 / 0.3415 | 48.53 / 48.46 | 1.4245 / 1.4228 | −0.0017 ± 0.0021 | 0.710 / 0.709 |

prophet-batch's accuracy is the same to the last digit as on macOS, Linux and Cloud Run.

## Checks (every run)

bit-identical forecasts for `n_jobs=1` and 16; log posterior ≥ Stan's on 1,437 / 1,437; no fallbacks; forecasts
identical across the 3 repetitions (stock and prophet-batch).

History: 0.1.0 on this laptop was 3.1× (default), before the Windows fix in 0.1.1; the fix's pre-release run gave
11.5× (see the prophet-batch README, Limitations).

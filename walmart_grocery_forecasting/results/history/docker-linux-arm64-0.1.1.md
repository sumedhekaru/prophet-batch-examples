> **Superseded (history).** Results on prophet-batch 0.1.1 from PyPI (2026-10-22). Current results, on 0.1.2 with `forecast_many`: [docker-linux-arm64.md](../docker-linux-arm64.md).

# Docker: Linux arm64 container on the Apple M4

2026-10-22 · image `prophet-batch-examples/walmart:local` ([envs/docker](../../envs/docker/)): Debian bookworm, Python
3.12.15, prophet 1.5.0 and **prophet-batch 0.1.1 from PyPI** (pinned in uv.lock) · Docker Desktop VM: Linux aarch64,
10 CPUs · examples `05e472d` · 1,437 M5 FOODS items, 28 days held out · 10 worker processes · **3 repetitions**:
median (min–max). Reproduce: `sh walmart_grocery_forecasting/envs/docker/build.sh && REPS=3 sh
walmart_grocery_forecasting/envs/docker/run.sh`. Every table: [docker-bench-20261022-004113.md](../docker-bench-20261022-004113.md).

Same pipeline and settings as the [macOS run](local-macos-m4-0.1.1.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, serial¹ | stock, 10-process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|
| default `Prophet()` | 317.1 | 57.2 | 19.0 (3.0×) | **6.7 (8.6×, 8.5–8.6)** |
| + M5 events as holidays | 417.8 | 75.3 | 20.7 (3.6×) | **9.0 (8.3×, 8.0–8.4)** |
| + events + SNAP regressors | 427.9 | 81.9 | 22.5 (3.6×) | **11.1 (7.4×, 7.2–7.7)** |

¹ Timed on 30 items, extrapolated. Everything is 5–30% slower than natively on macOS (the VM), prophet-batch a little
more than stock.

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | sMAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---|---:|---|
| default | 0.3450 / 0.3438 | 48.48 / 48.39 | 1.4277 / 1.4261 | −0.0015 ± 0.0023 | 0.722 / 0.720 |
| events | 0.3480 / 0.3470 | 48.94 / 48.87 | 1.4396 / 1.4377 | −0.0019 ± 0.0023 | 0.712 / 0.710 |
| events + SNAP | 0.3421 / 0.3415 | 48.54 / 48.46 | 1.4239 / 1.4228 | −0.0012 ± 0.0022 | 0.710 / 0.709 |

**Across platforms:** prophet-batch's forecasts here and on macOS agree to 3.5·10⁻⁹ (yhat and interval bounds, all
items and days); stock Prophet's differ by up to 11 units/day (Stan's L-BFGS stops at platform-dependent points),
which is why stock's accuracy differs in the last digits between the two pages and prophet-batch's does not.

## Checks (every run)

bit-identical forecasts for `n_jobs=1` and 10; log posterior ≥ Stan's on 1,437 / 1,437; no fallbacks; forecasts
identical across the 3 repetitions (stock and prophet-batch).

History: the pre-release run (0.1.0.dev0) gave 8.6× / 8.6× / 7.8×: [history/docker-linux-arm64.md](docker-linux-arm64-prerelease.md).

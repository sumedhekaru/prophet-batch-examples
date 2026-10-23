> **Pre-release record (history).** Made on 2026-10-21 with prophet-batch 0.1.0.dev0 from a local checkout (commit `3150f51`), before releases were on PyPI. Current results, on prophet-batch from PyPI: [docker-linux-arm64.md](../docker-linux-arm64.md).

# Docker: Linux arm64 container on the Apple M4

2026-10-21 · image `prophet-batch-examples/walmart:local` ([envs/docker](../../envs/docker/)): Debian bookworm, Python
3.12.15, prophet 1.5.0 + prophet-batch 0.1.0.dev0 (`3150f51`) from a wheel · Docker Desktop VM: Linux 6.12 aarch64,
10 CPUs, 8 GB · 1,437 M5 FOODS items, 28 days held out · 10 worker processes. Reproduce:
`sh walmart_grocery_forecasting/envs/docker/build.sh && sh walmart_grocery_forecasting/envs/docker/run.sh`.

Same pipeline and settings as the [macOS run](local-macos-m4-prerelease.md); prophet-batch keeps only the interval columns of each
forecast (`predict_many(columns=...)`), as the stock workers return only those.

## Speed: seconds for all 1,437 items (fit + forecast)

| model | stock, serial¹ | stock, 10-process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|
| default `Prophet()` | 306.8 | 59.8 | 19.7 (3.0×) | **7.0 (8.6×)** |
| + M5 events as holidays | 407.8 | 79.2 | 22.8 (3.5×) | **9.2 (8.6×)** |
| + events + SNAP regressors | 426.5 | 86.0 | 23.7 (3.6×) | **11.0 (7.8×)** |

¹ Timed on 30 items, extrapolated. Everything is 5–30% slower than natively on macOS (the VM), stock and prophet-batch
alike.

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---:|---|
| default | 0.3450 / 0.3438 | 1.4277 / 1.4261 | −0.0015 ± 0.0023 | 0.722 / 0.720 |
| events | 0.3480 / 0.3470 | 1.4396 / 1.4377 | −0.0019 ± 0.0023 | 0.712 / 0.710 |
| events + SNAP | 0.3421 / 0.3415 | 1.4239 / 1.4228 | −0.0012 ± 0.0022 | 0.710 / 0.709 |

## Same forecasts on macOS and Linux

prophet-batch's forecasts here match the macOS run to within 3·10⁻⁹ (floating-point round-off), intervals included:
the fits are exact optima and the draws come from per-series seeded generators. Stock Prophet's do not: the same item's
forecast differs by up to 10.9 units/day between the two platforms (Stan's L-BFGS stops at a platform-dependent point),
which is why its accuracy row above differs slightly from the macOS one.

## Checks (all variants)

Forecasts bit-identical for `n_jobs=1` and `10`; every fit's log posterior ≥ Stan's (1,437 / 1,437); no fallbacks.

An earlier run without `columns=` was killed by the container's 8 GB limit in the holiday variants: with 30 holidays a
full forecast frame has 112 columns, 2.3 GB for all items. `predict_many(columns=)` was added to prophet-batch for this.

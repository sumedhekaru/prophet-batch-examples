> **Superseded (history).** Results on prophet-batch 0.1.1 from PyPI (2026-10-22). Current results, on 0.1.2 with `forecast_many`: [cloudrun-us-east1.md](../cloudrun-us-east1.md).

# Cloud Run job, us-east1 (4 vCPU, 8 GiB)

2026-10-22 · Cloud Run job, one task, 4 vCPU / 8 GiB, us-east1 · image built from examples `05e472d` (linux/amd64,
Python 3.12.15, prophet 1.5.0 and **prophet-batch 0.1.1 from PyPI**) · data and results on a Cloud Storage bucket
mounted as a volume · 1,437 M5 FOODS items, 28 days held out · **3 repetitions** of every model variant, each an
execution on a fresh instance: median (min–max). Reproduce: [envs/cloudrun_job](../../envs/cloudrun_job/)
(`REPS=3 … deploy.sh`, then `teardown.sh`). Every table: [cloudrun-bench-20261022-001224.md](../cloudrun-bench-20261022-001224.md).

## Speed: seconds for all 1,437 items (fit + forecast), median of 3

| model | stock, serial¹ | stock, process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|
| default `Prophet()` | 939.3 | 254.4 | 83.9 (3.1×) | **23.6 (10.9×, 10.4–11.0)** |
| + M5 events as holidays | 1,263.1 | 310.6 | 79.3 (3.9×) | **28.0 (11.1×, 10.5–11.2)** |
| + events + SNAP regressors | 1,346.8 | 397.8 | 107.5 (3.7×) | **44.9 (8.9×, 8.8–9.0)** |

¹ Timed on 30 items, extrapolated. Speed-ups are against the stock pool of the same execution, which uses the same
worker count. Cloud Run's cores are ≈ 3× slower than the M4's; the speed-ups are close to the M4's (10.2× / 10.4× /
8.9×).

**Workers.** The pool and `n_jobs=-1` both use the CPUs the job may use (its CFS quota, cgroup v1). A "4 vCPU" job
landed on two instance shapes: 5 logical CPUs with a quota of 4 (6 of the 9 executions) or 6 logical CPUs with a quota
of 5 (default: repetition 1; events: repetitions 2–3). Times in the table mix the two; the per-execution tables are in
the full summary.

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---:|---|
| default | 0.3448 / 0.3438 | 1.4281 / 1.4261 | −0.0020 ± 0.0022 | 0.721 / 0.720 |
| events | 0.3483 / 0.3470 | 1.4401 / 1.4377 | −0.0024 ± 0.0022 | 0.711 / 0.710 |
| events + SNAP | 0.3420 / 0.3415 | 1.4233 / 1.4228 | −0.0006 ± 0.0021 | 0.710 / 0.709 |

prophet-batch's accuracy is the same to the last digit as on macOS and in the arm64 container; stock's moves slightly
between platforms (Stan's stopping point).

## Checks (every execution)

- Forecasts bit-identical for `n_jobs=1` and the job's worker count; every fit's log posterior ≥ Stan's (1,437 /
  1,437); no fallbacks.
- Across repetitions: identical on the same instance shape; between the two shapes prophet-batch differs by at most
  4.4·10⁻¹⁰ and stock by 1.1·10⁻¹³ (different hosts; the `n_jobs=1` path differs the same way, so it is the hardware,
  not the worker count).
- All GCP resources were deleted after the runs (`teardown.sh`).

History: the pre-release run (0.1.0.dev0, one execution per variant, 5–6 workers because the worker default then
missed cgroup v1) gave 10.6× / 10.3× / 8.8×: [history/cloudrun-us-east1.md](cloudrun-us-east1-prerelease.md).

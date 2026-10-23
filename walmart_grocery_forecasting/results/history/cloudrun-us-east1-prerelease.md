> **Pre-release record (history).** Made on 2026-10-21 with prophet-batch 0.1.0.dev0 from a local checkout (commit `9dc042e`, recorded as `d4f7824` before a history correction), before releases were on PyPI. Current results, on prophet-batch from PyPI: [cloudrun-us-east1.md](../cloudrun-us-east1.md).

# Cloud Run job, us-east1 (4 vCPU, 8 GiB)

2026-10-21 · Cloud Run job, one task, 4 vCPU / 8 GiB, us-east1 · image built from examples `d120a54` (linux/amd64,
Python 3.12.15, prophet 1.5.0, prophet-batch `d4f7824`) · data and results on a Cloud Storage bucket mounted as a volume
· 1,437 M5 FOODS items, 28 days held out. Reproduce: [envs/cloudrun_job](../../envs/cloudrun_job/) (`deploy.sh`, then
`teardown.sh`). Each model variant is one execution on a fresh machine; inside it every method runs one after another.

## Speed: seconds for all 1,437 items (fit + forecast)

| model | workers | stock, serial¹ | stock, process pool | prophet-batch, sampled history intervals | prophet-batch, analytic history intervals |
|---|---:|---:|---:|---:|---:|
| default `Prophet()` | 5 | 947.3 | 265.7 | 85.9 (3.1×) | **25.1 (10.6×)** |
| + M5 events as holidays | 5 | 1,195.4 | 382.7 | 102.2 (3.7×) | **37.1 (10.3×)** |
| + events + SNAP regressors | 6 | 1,333.8 | 340.4 | 88.9 (3.8×) | **38.8 (8.8×)** |

¹ Timed on 30 items, extrapolated. Speed-ups are against the stock pool with the same worker count. Cloud Run's cores
are ≈ 3× slower than the M4's (stock serial: 660 vs 200 ms per series); the speed-ups are close to the M4's (10.2× /
10.3× / 8.6×).

**Workers.** The job gets a CFS quota of ≈ 3.7–3.9 CPUs (cgroup v1, `cfs_quota_us` 322600–394500 per 100000) on a
machine showing 5–6 CPUs. prophet-batch's `n_jobs=-1` resolves this to 4 (checked in the job), but the pipeline's
worker default then read only cgroup v2 and used 5–6 workers, for stock and prophet-batch alike: slightly
oversubscribed, fair, a little slower than necessary. Fixed afterwards (the default now reads v1 too).

## Accuracy on the 28 held-out days

| model | WAPE stock / batch | MASE stock / batch | Δ MASE (± 2 SE) | 80% coverage stock / batch |
|---|---|---|---:|---|
| default | 0.3448 / 0.3438 | 1.4281 / 1.4261 | −0.0020 ± 0.0022 | 0.721 / 0.720 |
| events | 0.3483 / 0.3470 | 1.4401 / 1.4377 | −0.0024 ± 0.0022 | 0.711 / 0.710 |
| events + SNAP | 0.3420 / 0.3415 | 1.4233 / 1.4228 | −0.0006 ± 0.0021 | 0.710 / 0.709 |

prophet-batch's accuracy is the same to the last digit as on macOS and in the arm64 container; stock's moves slightly
between platforms (Stan's stopping point).

## Checks (all variants)

Forecasts bit-identical for `n_jobs=1` and 5 (6); every fit's log posterior ≥ Stan's (1,437 / 1,437); no fallbacks.
All GCP resources were deleted after the runs (`teardown.sh`).

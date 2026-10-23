# Cloud Run job: 8 vCPU / 32 GiB, us-east1: the three large public datasets

2026-10-22 · Cloud Run job (us-east1), 8 vCPU / 32 GiB, one task, the [Docker image](../envs/docker/) built for
linux/amd64 · Python 3.12.15 · prophet 1.5.0 and **prophet-batch 0.1.2, both from PyPI** (image from examples
`d5f2058`) · **9 executions** (3 per dataset, each on a fresh instance; the three datasets side by side) · median
(min–max). Reproduce: `REPS=3 SIDE_BY_SIDE=1 PROJECT=... REGION=... BUCKET=... sh public_datasets/envs/cloudrun_job/deploy.sh`
([how it works](../envs/cloudrun_job/README.md)). Every table: [cloudrun-bench-20261022-181716.md](cloudrun-bench-20261022-181716.md).

**Workers.** An "8 vCPU" job got 9, 8 or 7 usable CPUs (the CPU quota), depending on the host (AMD EPYC 7B13 or Intel
Xeon); the pipeline and prophet-batch's `n_jobs=-1` follow the quota, so both methods use the same count in each
execution, and every speed-up is computed within one execution.

## Speed: fit + forecast of every series, against stock Prophet in a process pool on the same instance

| dataset | series | runs | stock, process pool | `forecast_many`, analytic history intervals | `forecast_many`, sampled (default) | `fit_many` + `predict_many`, analytic |
|---|---:|---:|---:|---:|---:|---:|
| M5 item × store | 30,490 | 3 | 2,165.9 s | **156.7 s (13.8×, 12.8–14.0)** | 694.3 s (3.1×) | 197.9 s (10.9×) |
| M4 Daily | 4,227 | 3 | 862.0 s | **31.1 s (27.7×, 22.2–27.9)** | 123.9 s (7.0×) | 39.2 s (21.9×) |
| M5 item | 3,049 | 3 | 236.3 s | **17.6 s (13.5×, 12.2–13.5)** | 69.3 s (3.4×) | 22.7 s (10.4×) |

## Accuracy on the held-out steps (first run of each dataset)

| dataset | WAPE stock / prophet-batch | sMAPE stock / prophet-batch | MASE stock / prophet-batch | Δ MASE (± 2 SE) | 80% coverage stock / prophet-batch |
|---|---|---|---|---:|---|
| M5 item × store | 0.7692 / 0.7687 | 143.11 / 143.09 | 1.6443 / 1.6428 | −0.0015 ± 0.0003 | 0.785 / 0.784 |
| M4 Daily | 0.1057 / 0.1052 | 11.66 / 11.61 | 11.9655 / 11.8888 | −0.0767 ± 0.0316 | 0.419 / 0.414 |

## Checks (every execution)


- M5 item × store: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock max |Δ| 2.8e-14, prophet-batch max |Δ| 1.5e-09.
- M4 Daily: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock max |Δ| 3.6e-12, prophet-batch max |Δ| 4.2e-07.
- M5 item: n_jobs=1 vs many bit-identical in every run: yes; log posterior ≥ Stan's: min share 1.0000; fallbacks: 0; forecasts across repetitions: stock max |Δ| 1.1e-13, prophet-batch max |Δ| 8.9e-10.

Repetitions ran on different host CPUs, so their forecasts differ by floating-point rounding (≤ 4·10⁻⁷ on M4 Daily's
values in the thousands; ≤ 1.5·10⁻⁹ on M5).

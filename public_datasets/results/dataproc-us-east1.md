# Spark: Dataproc Serverless, us-east1: the three large public datasets

2026-10-23 · the protocol of the [walmart Spark benchmark](../../walmart_grocery_forecasting/results/dataproc-us-east1.md):
one method per batch, 3 repetitions each in alternating order, every phase timed from the platform's batch records
and the driver · runtime 2.3 (Spark 3.5.3) · driver 4 cores + 2 executors × 4 cores · default `Prophet()`, history +
the held-out steps · stock: one series per task; prophet-batch: `fit_many` + `predict_many` (analytic history
intervals) on each of 32 groups · a timed warm-up phase for both · image: prophet 1.5.0 + **prophet-batch 0.1.2 from
PyPI**, examples `d5f2058` · reproduce: `REPS=3 JOB_ARGS="--warmup --groups 32" PROJECT=… REGION=us-east1 BUCKET=…
sh public_datasets/envs/dataproc/benchmark.sh` ([how it works](../envs/dataproc/README.md)). 18 batches, all succeeded.

## The gain grows with the job

| job | stock, end to end | prophet-batch, end to end | **end to end** | execute only |
|---|---:|---:|---:|---:|
| Walmart, 1,437 items ([page](../../walmart_grocery_forecasting/results/dataproc-us-east1.md)) | 403 s | 181 s | **2.2×** | 9.8× |
| M5 item, 3,049 series | 670 s | 213 s | **3.2×** | 10.9× |
| M4 Daily, 4,227 long series | 1,809 s | 275 s | **6.6×** | 18.6× |
| M5 item × store, 30,490 series | 4,788 s (80 min) | 710 s (12 min) | **6.7×** | 11.4× |

Each batch spends ≈ 130–290 s on provisioning, starting the driver and executors, loading the data and warming up the
Python workers, the same for both methods. On a small job that is most of prophet-batch's batch; on a large one it is
not, and the end-to-end gain approaches the execution gain. Both methods used both hosts and all 8 cores (stock 93%
core utilisation during execute on item × store, prophet-batch 73%: 32 groups on 8 cores leave the last wave partly
idle). Medians of 3 batches; per-repetition values in the full tables.

## M5 item × store, 30,490 series ([full tables](dataproc-bench-20261022-224946-m5_item_store.md))

| phase (s, median (min–max)) | stock: one series per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 65.7 (65.6–75.4) | 65.6 (65.1–110.8) |
| driver start | 31.4 (30.1–35.3) | 29.7 (29.4–62.6) |
| executors registered | 7.6 (7.1–9.1) | 8.6 (3.3–11.1) |
| data load | 157.6 (154.8–159.2) | 162.2 (150.2–181.7) |
| warm-up (Python workers started, Prophet imported) | 13.6 (13.0–14.0) | 13.4 (13.1–15.4) |
| **execute** | **4479.5 (4113.1–4583.5)** | **392.0 (347.7–402.9)** |
| post (accuracy, write) | 26.1 (26.1–26.6) | 22.5 (17.6–25.5) |
| shutdown | 8.0 (7.9–8.3) | 6.6 (6.4–6.6) |
| **end to end** | **4787.6 (4437.2–4893.9)** | **710.3 (644.1–795.7)** |

## M4 Daily, 4,227 series ([full tables](dataproc-bench-20261022-224946-m4_daily.md))

| phase (s, median (min–max)) | stock: one series per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 65.8 (59.8–69.4) | 70.4 (65.7–71.7) |
| driver start | 29.8 (29.6–29.8) | 30.6 (29.7–32.7) |
| executors registered | 8.6 (7.6–9.1) | 8.6 (8.2–9.6) |
| data load | 45.0 (44.0–45.5) | 48.6 (45.7–51.9) |
| warm-up (Python workers started, Prophet imported) | 13.9 (12.9–14.2) | 14.3 (14.2–14.6) |
| **execute** | **1635.4 (1608.8–1732.6)** | **88.0 (86.6–95.4)** |
| post (accuracy, write) | 5.2 (5.1–5.5) | 5.1 (5.0–5.8) |
| shutdown | 5.2 (5.0–5.4) | 5.2 (5.1–5.5) |
| **end to end** | **1809.3 (1774.4–1909.5)** | **275.1 (266.3–276.5)** |

## M5 item, 3,049 series ([full tables](dataproc-bench-20261022-224946-m5_item.md))

| phase (s, median (min–max)) | stock: one series per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 67.1 (64.2–70.4) | 69.8 (65.2–70.5) |
| driver start | 29.8 (29.7–30.1) | 30.1 (29.3–30.8) |
| executors registered | 8.6 (8.1–10.1) | 8.6 (8.6–11.1) |
| data load | 34.8 (34.3–37.7) | 35.6 (35.5–36.2) |
| warm-up (Python workers started, Prophet imported) | 14.5 (13.6–15.2) | 14.2 (13.9–14.4) |
| **execute** | **505.3 (502.5–510.2)** | **46.4 (44.9–50.1)** |
| post (accuracy, write) | 4.8 (4.7–4.9) | 4.4 (4.4–4.7) |
| shutdown | 4.6 (4.4–6.3) | 4.7 (4.4–4.8) |
| **end to end** | **670.1 (663.0–682.7)** | **212.7 (209.9–220.2)** |

## Accuracy and reproducibility

Same accuracy as stock in every job (MASE stock / prophet-batch: item × store 1.6443 / 1.6428, M4 Daily 11.9655 /
11.8888, M5 item 1.3647 / 1.3626), and forecasts identical across the 3 repetitions for both methods.

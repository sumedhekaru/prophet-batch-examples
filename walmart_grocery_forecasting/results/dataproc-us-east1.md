# Spark: Dataproc Serverless, us-east1

2026-10-22 · reproducible Spark benchmark (protocol: every phase timed from the platform's batch records and the
driver; full tables: [dataproc-bench-20261022-221855.md](dataproc-bench-20261022-221855.md)). Runtime 2.3 (Spark
3.5.3) · driver 4 cores + 2 executors × 4 cores · 1,437 M5 FOODS items, history + 28 days · one method per batch, 3
repetitions each, alternating order, a timed warm-up phase for both, 32 groups for prophet-batch · image: prophet 1.5.0
+ **prophet-batch 0.1.2 from PyPI**, examples `d5f2058` · reproduce: `REPS=3 JOB_ARGS="--warmup --groups 32"
PROJECT=… REGION=us-east1 BUCKET=… sh walmart_grocery_forecasting/envs/dataproc/benchmark.sh`.

| phase (s, median (min–max)) | stock: one item per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 69.5 (65.2–70.9) | 65.2 (64.5–65.9) |
| driver start | 30.6 (30.0–32.4) | 29.4 (29.2–33.4) |
| executors registered | 7.6 (7.1–8.6) | 8.6 (7.6–9.6) |
| data load | 24.7 (24.4–27.8) | 25.9 (24.0–26.1) |
| warm-up (Python workers started, Prophet imported) | 16.1 (16.0–17.0) | 16.1 (15.1–17.7) |
| **execute** | **244.1 (240.7–250.6)** | **25.0 (24.3–25.8)** |
| post (accuracy, write) | 3.9 (3.8–4.2) | 3.9 (3.6–3.9) |
| shutdown | 5.6 (5.5–6.3) | 5.3 (4.5–6.4) |
| **end to end** | **403.4 (400.7–408.3)** | **181.2 (173.4–186.3)** |

- **Execution speed-up 9.8×** (per repetition 9.8×, 10.3×, 9.3×); **end to end 2.2×** (2.2×, 2.4×, 2.2×). About
  130 s of every batch is platform setup, data load and warm-up, the same for both methods; on the larger public
  datasets the end-to-end gain grows to 6.7× ([public_datasets on Dataproc](../../public_datasets/results/dataproc-us-east1.md)).
- Both used the whole cluster: 2 hosts, 8 processes, 8 tasks at a time; core utilisation during execute: stock 89%,
  prophet-batch 64% (32 groups on 8 cores: the last wave is partly idle).
- Same accuracy: WAPE 0.3448 (stock) / 0.3438, MASE 1.4281 / 1.4261, 80% coverage 0.721 / 0.720. Forecasts are
  identical across the 3 repetitions, for both methods.

Earlier results: [0.1.1](history/dataproc-us-east1-0.1.1.md) (9.7× / 1.9×), [pre-release](history/dataproc-us-east1-prerelease.md).

> **Pre-release record (history).** Made on 2026-10-21 with prophet-batch 0.1.0.dev0 from a local checkout (commit `9dc042e`), before releases were on PyPI. Current results, on prophet-batch from PyPI: [dataproc-us-east1.md](../dataproc-us-east1.md).

# Spark on Dataproc Serverless (us-east1)

**Reproducible benchmark, 2026-10-21, with a warm-up phase** (full tables and every run:
[dataproc-bench-20261021-warmup.md](dataproc-bench-20261021-warmup.md)). Runtime 2.3 (Spark 3.5.3) · driver 4 cores +
2 executors × 4 cores · 1,437 M5 FOODS items, history + 28 days · one method per batch, 3 repetitions each,
alternating order · prophet-batch commit `9dc042e` (recorded as `d4f7824`, its ID before the history correction) ·
reproduce: `REPS=3 JOB_ARGS=--warmup PROJECT=… REGION=us-east1 BUCKET=… sh walmart_grocery_forecasting/envs/dataproc/benchmark.sh`.

| phase (s, median (min–max)) | stock: one item per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 86.3 (79.9–90.2) | 85.4 (79.7–88.3) |
| driver start | 34.5 (34.5–35.4) | 36.5 (34.7–54.1) |
| executors registered | 10.1 (9.6–10.1) | 10.1 (9.1–10.6) |
| data load | 25.2 (24.9–25.9) | 27.7 (24.6–28.4) |
| warm-up (Python workers started, Prophet imported) | 16.4 (15.8–16.6) | 17.1 (16.3–18.9) |
| **execute** | **255.1 (248.1–260.1)** | **26.5 (25.9–33.0)** |
| post (accuracy, write) | 4.5 (4.5–4.8) | 4.5 (4.4–5.0) |
| shutdown | 4.7 (3.6–6.3) | 4.9 (4.8–5.3) |
| **end to end** | **436.5 (432.9–438.0)** | **210.5 (206.2–239.2)** |

- **Execution speed-up 9.6×** (per repetition 7.7×, 9.6×, 9.8×); **end to end 2.1×** (1.8×, 2.1×, 2.1×).
- Both used the whole cluster: 2 hosts, 8 processes, 8 tasks at a time; core utilisation during execute: stock 89%,
  prophet-batch 65%.
- Same accuracy (WAPE 0.3448 / 0.3438, MASE 1.4281 / 1.4261); each method's forecasts identical in all 3 runs.
- About 190 s of each batch is platform setup, load and warm-up, the same for both methods: for a job of this size
  the platform dominates end to end; the execution speed-up is what grows with more series per batch.

**Why a warm-up phase** (track F6): without it, the first ≈ 13–16 s of the execute phase were cold Python workers
starting and importing Prophet (≈ 5 s per worker on Dataproc), which left prophet-batch's cores 58% idle. The warm-up
runs a tiny pandas UDF on every core first (it must be a pandas UDF: Spark's RDD tasks use a separate Python worker
pool) and is timed as its own phase, for both methods. Group count was checked too: 32 or 64 groups (4–8 per core)
work best; 8 or 16 leave cores idle.

**Earlier runs, superseded:** the same benchmark without warm-up gave 6.5× execute (stock 263.5 s, prophet-batch 40.3 s)
and 2.0× end to end ([dataproc-bench-20261021.md](dataproc-bench-20261021.md)); runs on runtime 3.0 (incl. 13.3×) were
single-threaded, because runtime 3.0 sets `spark.master=local` for PySpark batches (see the env README).

> **Superseded (history).** Results on prophet-batch 0.1.1 from PyPI (2026-10-22). Current results, on 0.1.2 with `forecast_many`: [dataproc-us-east1.md](../dataproc-us-east1.md).

# Spark on Dataproc Serverless (us-east1)

**Reproducible benchmark, 2026-10-22, prophet-batch 0.1.1 from PyPI** (full tables and every run:
[dataproc-bench-20261022-051440.md](../dataproc-bench-20261022-051440.md)). Runtime 2.3 (Spark 3.5.3) · driver 4 cores +
2 executors × 4 cores · 1,437 M5 FOODS items, history + 28 days · one method per batch, 3 repetitions each,
alternating order, a timed warm-up phase for both · image: prophet 1.5.0 + prophet-batch 0.1.1 from PyPI, examples
`05e472d` · reproduce: `REPS=3 JOB_ARGS=--warmup PROJECT=… REGION=us-east1 BUCKET=… sh walmart_grocery_forecasting/envs/dataproc/benchmark.sh`.

| phase (s, median (min–max)) | stock: one item per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 85.2 (85.1–85.8) | 90.7 (84.3–105.2) |
| driver start | 35.8 (35.6–36.0) | 35.8 (35.7–62.4) |
| executors registered | 9.1 (8.6–10.1) | 9.1 (9.1–10.6) |
| data load | 24.6 (24.0–25.7) | 25.4 (25.1–26.8) |
| warm-up (Python workers started, Prophet imported) | 15.8 (15.3–15.9) | 16.1 (14.6–17.5) |
| **execute** | **234.5 (229.2–242.9)** | **24.2 (23.1–26.7)** |
| post (accuracy, write) | 4.4 (4.3–5.0) | 4.7 (4.6–4.9) |
| shutdown | 4.9 (4.7–5.1) | 6.3 (6.2–7.6) |
| **end to end** | **413.9 (409.6–424.0)** | **213.1 (209.6–253.8)** |

- **Execution speed-up 9.7×** (per repetition 9.9×, 8.8×, 10.0×); **end to end 1.9×** (1.6×, 2.0×, 2.0×; the 1.6×
  is one prophet-batch batch whose platform start took 44 s longer than the others: provision 105 s, driver 62 s).
- Both used the whole cluster: 2 hosts, 8 processes, 8 tasks at a time; core utilisation during execute: stock 89%,
  prophet-batch 63%.
- Same accuracy (WAPE 0.3448 / 0.3438, MASE 1.4281 / 1.4261, coverage 0.721 / 0.720); each method's forecasts
  identical in all 3 runs.
- About 185 s of each batch is platform setup, load and warm-up, the same for both methods: for a job of this size
  the platform dominates end to end; the execution speed-up is what grows with more series per batch.

**Why a warm-up phase** (track F6): without it, the first ≈ 13–16 s of the execute phase were cold Python workers
starting and importing Prophet (≈ 5 s per worker on Dataproc), which left prophet-batch's cores 58% idle. The warm-up
runs a tiny pandas UDF on every core first (it must be a pandas UDF: Spark's RDD tasks use a separate Python worker
pool) and is timed as its own phase, for both methods. Group count was checked too: 32 or 64 groups (4–8 per core)
work best; 8 or 16 leave cores idle.

**History** (pre-release, prophet-batch 0.1.0.dev0 from a local checkout): the same benchmark gave 9.6× execute and
2.1× end to end ([history/dataproc-us-east1.md](dataproc-us-east1-prerelease.md)); without warm-up 6.5×; runs on
runtime 3.0 (incl. 13.3×) were single-threaded, because runtime 3.0 sets `spark.master=local` for PySpark batches
(see the env README).

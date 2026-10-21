# Spark on Dataproc Serverless (us-east1)

**Reproducible benchmark, 2026-10-21** (full tables and every run: [dataproc-bench-20261021.md](dataproc-bench-20261021.md)).
Runtime 2.3 (Spark 3.5.3) · driver 4 cores + 2 executors × 4 cores · 1,437 M5 FOODS items, history + 28 days ·
one method per batch, 3 repetitions each, alternating order · reproduce:
`PROJECT=… REGION=us-east1 BUCKET=… sh walmart_grocery_forecasting/envs/dataproc/benchmark.sh`.

| phase (s, median (min–max)) | stock: one item per task | prophet-batch: `fit_many` per group |
|---|---:|---:|
| provision (created → running) | 85.9 (85.8–90.9) | 90.7 (90.5–97.7) |
| driver start | 35.0 (34.5–36.7) | 36.8 (35.9–61.7) |
| executors registered | 11.1 (10.1–12.1) | 9.1 (8.1–10.6) |
| data load | 26.1 (25.7–26.6) | 26.0 (24.8–29.9) |
| **execute** | **263.5 (258.1–265.9)** | **40.3 (37.7–41.7)** |
| post (accuracy, write) | 1.2 (1.1–1.3) | 1.3 (1.1–1.3) |
| shutdown | 5.0 (4.9–5.0) | 5.0 (4.9–5.1) |
| **end to end** | **427.7 (422.1–436.7)** | **210.2 (208.4–241.4)** |

- **Execution speed-up 6.5×** (per repetition 7.0×, 6.6×, 6.2×); **end to end 2.0×** (1.8×, 2.1×, 2.0×): ≈ 160 s of
  each batch is platform setup and data load, the same for both methods.
- Both used the whole cluster: 2 hosts, 8 processes, 8 tasks at a time (per-task records). Core utilisation during
  execute: stock 84%, prophet-batch 42%; prophet-batch's 32 groups leave cores idle at the end (room to improve).
- Same accuracy (WAPE 0.3448 / 0.3438, MASE 1.4281 / 1.4261), and each method's forecasts identical in all 3 runs.

**Earlier, superseded:** runs on runtime 3.0 (incl. a 13.3× figure) ran Spark in local mode on one thread: runtime
3.0 sets `spark.master=local` for PySpark batches (diagnosed with `envs/dataproc/diag.py`; see the env README).

**Local Spark cluster (Docker on the M4):** the job and image also work on a standalone master + 2 executors; local
numbers there are behaviour checks, not benchmarks.

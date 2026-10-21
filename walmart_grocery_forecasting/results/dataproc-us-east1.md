# Spark: Dataproc Serverless (us-east1) and a local Spark cluster

2026-10-21 · job [pipeline/spark_job.py](../pipeline/spark_job.py), image [envs/dataproc](../envs/dataproc/) (Debian 12,
Python 3.12, prophet 1.5.0, prophet-batch `d4f7824`, pandas 2.2.3, pyarrow 19) · 1,437 M5 FOODS items, 28 days held
out · prophet-batch: items hashed into 16 groups, `fit_many` + `predict_many` per group (`applyInPandas`); stock: one
`Prophet` per item per task (`applyInPandas`), the usual Spark pattern.

## Dataproc Serverless (runtime 3.0, Spark 4.0.2)

| method | wall s, all 1,437 items | vs stock |
|---|---:|---:|
| stock, one item per task | 1,192.9 | 1.0× |
| prophet-batch, `fit_many` per group | **90.0** | **13.3×** |

Accuracy: WAPE 0.3448 / 0.3438, MASE 1.4281 / 1.4261, 80% coverage 0.721 / 0.720 (stock / prophet-batch); Δ MASE
−0.0020 ± 0.0022; log posterior ≥ Stan's on 100% of items (the same numbers as on Cloud Run, an x86 platform too).

**Caveat: this ran on one core.** We asked for a 4-core driver and 2 executors × 4 cores, but Spark ran in local mode
inside the driver (the job saw a `local` master and no executors), and the stock tasks' own times add up to the wall
time, so the tasks ran one at a time. The comparison is fair (both methods in the same mode), and close to other
single-process results (Cloud Run 15×), but it is not a multi-executor result. Why Dataproc chose local mode is open.

## Local Spark cluster (Docker on the M4; Spark 4.0.1, native arm64)

| setup | prophet-batch, all items | stock, 40 items extrapolated | speed-up |
|---|---:|---:|---:|
| local mode, 4 cores | 9.7 s | 348.4 s | 35.9× |
| standalone master + 2 executors × 2 cores + driver | 10.1 s | 367.8 s | 36.3× |

These show the job and image work with executors in separate containers. The speed-ups overstate the gap: the
stock time is extrapolated from 40 items, which also multiplies Spark's fixed per-job overhead, and all containers
shared one Mac. Reproduce: `envs/dataproc/local/` (Dockerfile + `cluster.sh`).

All GCP resources were deleted after the runs (`teardown.sh`).

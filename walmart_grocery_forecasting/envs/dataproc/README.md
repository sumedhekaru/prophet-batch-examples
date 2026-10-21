# Dataproc Serverless (Spark)

The use case as a PySpark job ([pipeline/spark_job.py](../../pipeline/spark_job.py)): prophet-batch fits groups of
items with `fit_many` inside `applyInPandas` (many series per task), against stock Prophet with one item per task.
Results: [results/dataproc-us-east1.md](../../results/dataproc-us-east1.md).

```sh
PROJECT=my-project REGION=us-east1 BUCKET=my-bucket sh walmart_grocery_forecasting/envs/dataproc/deploy.sh
PROJECT=my-project REGION=us-east1 BUCKET=my-bucket sh walmart_grocery_forecasting/envs/dataproc/teardown.sh
```

**Image** ([Dockerfile](Dockerfile)): follows Google's custom-container rules: Debian 12, `procps` + `tini`, user
`spark` (uid/gid 1099), no Spark or Java (Dataproc mounts them), `PYSPARK_PYTHON` set to our Python. Its pins differ
from the repo's `uv.lock`: Dataproc's pyspark needs pandas 2.x and pyarrow for pandas UDFs.

**Project prerequisites** (found the hard way): APIs Dataproc, Compute Engine, Cloud Resource Manager and Container
File System; Private Google Access on the subnet (`deploy.sh` turns it on, `teardown.sh` back off); runtime 3.0 runs
workloads with end-user credentials by default, so `deploy.sh` runs them as the default compute service account.

**Local testing** ([local/](local/)): the image plus a Java 21 JRE and pyspark 4.0.1. `cluster.sh` starts a master, two
workers and a driver in separate containers. Note: the workers need a writable `SPARK_WORKER_DIR` (uid 1099).

**Gotchas (each cost a run to find):**
- **Use runtime 2.3, not 3.0.** Runtime 3.0 runs PySpark batches in local mode (`spark.master=local`, one thread, no
  executors), with any container or properties; 2.2 / 2.3 give a real cluster. Check with `diag.py` / `diag.sh`.
- **Turn off partition coalescing** for many-small-models work: adaptive execution merges the post-shuffle partitions
  of small-in-bytes data into one or two tasks, which then run the groups serially. The job sets
  `spark.sql.adaptive.coalescePartitions.enabled=false` and 4 shuffle partitions per core.
- Spark 3.5 on Python 3.12 needs `setuptools` (pyspark imports `distutils`); Dataproc's pyspark needs pandas 2.x.
- Local Spark from pip as uid 1099: give workers a writable `SPARK_WORKER_DIR`; submit `spark_main.py`, not the module.

**Benchmark** (reproducible, every phase timed separately): `benchmark.sh` builds and pushes the image, runs each
method `REPS` times (one method per batch, alternating order), saves every run's records and the batch resources
(state history, DCU usage), writes `summary.md` with `pipeline/spark_summary.py`, and tears everything down.

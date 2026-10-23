# Dataproc Serverless (Spark): the public datasets

The datasets as a PySpark job ([pipeline/spark_job.py](../../pipeline/spark_job.py)), with the same job code as the
[walmart Spark benchmark](../../../walmart_grocery_forecasting/envs/dataproc/README.md) (it lives in
[examples_core/spark.py](../../../examples_core/spark.py)): prophet-batch fits groups of series with `fit_many` inside
`applyInPandas` (many series per task), against stock Prophet with one series per task. Every phase is timed (platform
start, executors, load, warm-up, execute, write, shutdown), from the platform's batch records and the driver.

```sh
PROJECT=my-project REGION=us-east1 BUCKET=my-bucket REPS=3 JOB_ARGS="--warmup --groups 32" \
  sh public_datasets/envs/dataproc/benchmark.sh          # image, data, 3 × (batch, stock) per dataset, summary, teardown
```

`benchmark.sh` builds the image ([Dockerfile](Dockerfile): the walmart image's pins with this use case installed),
uploads the datasets, runs each method `REPS` times per dataset (`DATASETS`, default the three large ones; one method
per batch, alternating order), saves every run's records and batch resources, writes a `summary.md` per dataset
([examples_core/spark_summary.py](../../../examples_core/spark_summary.py)) and tears everything down (`TEARDOWN=0`
keeps it). The driver reads the dataset's raw files from the bucket and loads it with
[pipeline/data.py](../../pipeline/data.py), exactly as the local runs do. Local test on a Spark standalone cluster in
Docker: `IMG=prophet-batch-examples/public-spark:local-test MAIN=public_datasets/envs/dataproc/spark_main.py DATA=data
sh walmart_grocery_forecasting/envs/dataproc/local/cluster.sh --dataset m4_daily --n 40 --method batch`.

Status: run on GCP on 2026-10-22/23 (prophet-batch 0.1.2 from PyPI, 18 batches): [results](../../results/dataproc-us-east1.md);
the resources were deleted afterwards.

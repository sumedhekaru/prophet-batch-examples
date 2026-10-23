# Cloud Run job: the public datasets

The [Docker](../docker/) image, built for linux/amd64, run as a [Cloud Run job](https://cloud.google.com/run/docs/create-jobs)
with one task, as for the [walmart use case](../../../walmart_grocery_forecasting/envs/cloudrun_job/README.md). A Cloud
Storage bucket is mounted as a volume at `/mnt/gcs`: the container reads the datasets from `/mnt/gcs/data` and writes
its results to `/mnt/gcs/results` as ordinary files.

```sh
sh public_datasets/envs/cloudrun_job/build.sh                              # image prophet-batch-examples/public-datasets:amd64
REPS=3 SIDE_BY_SIDE=1 PROJECT=my-project REGION=us-east1 BUCKET=my-bucket \
  sh public_datasets/envs/cloudrun_job/deploy.sh                           # push, deploy, 3 executions per dataset
PROJECT=my-project REGION=us-east1 BUCKET=my-bucket sh public_datasets/envs/cloudrun_job/teardown.sh
```

`deploy.sh` creates an Artifact Registry repository and the bucket if they are missing, uploads the verified datasets
**already extracted** (so the job only reads the bucket), deploys the job (default 8 vCPU / 32 GiB: `CPU` / `MEMORY`;
M5 item × store needs ≈ 10 GB; one task, four-hour timeout, no retries) and runs one execution per dataset
(`DATASETS`, default the three large ones) `REPS` times. `SIDE_BY_SIDE=1` runs the datasets at the same time (each
execution gets its own instance; one dataset's repetitions stay in order). Results land in
`gs://$BUCKET/results/cloudrun-bench-<stamp>/` and are copied to `results/runs/`, with `summary.md`.

**Workers.** Cloud Run limits CPUs with a CFS quota that `os.cpu_count()` does not see; the pipeline and prophet-batch's
`n_jobs=-1` read it. An "8 vCPU" job got 7, 8 or 9 usable CPUs depending on the host, so speed-ups are computed within
one execution (both methods on the same instance).

Status: run on GCP on 2026-10-22 (prophet-batch 0.1.2 from PyPI, 3 repetitions): [results](../../results/cloudrun-us-east1.md);
the resources were deleted afterwards.

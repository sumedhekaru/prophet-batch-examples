# Cloud Run job

The [Docker](../docker/) image, built for linux/amd64, run as a [Cloud Run job](https://cloud.google.com/run/docs/create-jobs)
with one task. A Cloud Storage bucket is mounted as a volume at `/mnt/gcs`, so the container reads the data from
`/mnt/gcs/data/m5` and writes its results to `/mnt/gcs/results` as ordinary files: no Cloud Storage client in the
image, and the same pipeline as everywhere else.

```sh
sh walmart_grocery_forecasting/envs/cloudrun_job/build.sh                    # image prophet-batch-examples/walmart:amd64
sh walmart_grocery_forecasting/envs/cloudrun_job/simulate.sh --n 20          # local simulation (see below)
PROJECT=my-project REGION=us-central1 BUCKET=my-bucket MODEL=default \
  sh walmart_grocery_forecasting/envs/cloudrun_job/deploy.sh                 # push, deploy, execute
```

`deploy.sh` creates an Artifact Registry repository and the bucket if they are missing, copies the verified M5
archive to `gs://$BUCKET/data/m5/`, deploys the job (default 4 vCPU, 8 GiB: `CPU` / `MEMORY`; one task, one-hour timeout, no retries) and
runs one execution per model variant (`MODELS`), then copies the results to `results/runs/`. Results land in `gs://$BUCKET/results/` (`cloudrun-<model>-1437-<timestamp>.{json,npz,md}`).

**Local simulation.** `simulate.sh` runs the amd64 image with a local directory (`data/fake-bucket/`) mounted where
the job mounts the bucket, with the job's environment variables and `--cpus 8`. On Apple Silicon the image runs
under emulation, so it checks behaviour, not speed.

**Workers.** Cloud Run limits CPUs with a cgroup v1 CFS quota (a 4-vCPU job: ≈ 3.7–3.9 CPUs on a machine showing
5–6), which `os.cpu_count()` does not see. The pipeline's default worker count and prophet-batch's `n_jobs=-1` both
read the quota, so a 4-vCPU job runs 4 workers on both sides.

Status: run on GCP on 2026-10-22 (4 vCPU / 8 GiB, us-east1, 3 repetitions, prophet-batch 0.1.1 from PyPI): [results](../../results/cloudrun-us-east1.md); the
resources were deleted afterwards with `teardown.sh`.

**Benchmark mode.** `REPS=3` runs every model variant 3 times into `results/runs/<env>-bench-<stamp>/` and writes
`summary.md` there with [pipeline/bench_summary.py](../../pipeline/bench_summary.py): each time as median (min–max),
speed-ups computed within each run, accuracy, checks, and whether repetitions gave identical forecasts.

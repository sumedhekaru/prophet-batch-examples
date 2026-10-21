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
archive to `gs://$BUCKET/data/m5/`, deploys the job (8 vCPU, 32 GiB, one task, one-hour timeout, no retries) and
runs it. Results land in `gs://$BUCKET/results/` (`cloudrun-<model>-1437-<timestamp>.{json,npz,md}`).

**Local simulation.** `simulate.sh` runs the amd64 image with a local directory (`data/fake-bucket/`) mounted where
the job mounts the bucket, with the job's environment variables and `--cpus 8`. On Apple Silicon the image runs
under emulation, so it checks behaviour, not speed.

**Workers.** Cloud Run limits CPUs with a cgroup quota, which `os.cpu_count()` does not see. The pipeline's default
worker count and prophet-batch's `n_jobs=-1` both read the quota, so an 8-vCPU job runs 8 workers on both sides.

Status: image and local simulation work; `deploy.sh` has not been run on GCP yet.
